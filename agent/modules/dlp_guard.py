import pydivert
import socket
import re
import sys
import subprocess
import shutil
import time
import psutil
import httpx
from typing import List, Set, Optional
from datetime import datetime
from collections import defaultdict
from agent.core.logger import Logger
from agent.utils.registry import get_registry_manager
from agent.utils.firewall import FirewallManager

class DataLossGuard:
    # High-risk upload/file sharing and messaging sites
    UPLOAD_SITE_BLACKLIST = [
        "wetransfer.com", "mega.nz", "dropbox.com", "drive.google.com", 
        "mediafire.com", "web.whatsapp.com", "web.telegram.org"
    ]

    def __init__(self, logger: Logger, block_all: bool = False, whitelist: List[str] = None):
        self.logger = logger
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))
        self._running = False
        self._thread = None
        self._registry_manager = get_registry_manager()
        self._firewall_manager = FirewallManager() if sys.platform == 'win32' else None
        self._traffic_history = defaultdict(list)
        self._approved_hashes = set() # Set of SHA256 strings
        self._last_approval_sync = 0
        
    def _sync_approved_hashes(self, dashboard_url: str, api_key: str):
        """Fetch approved file hashes from dashboard."""
        try:
            url = f"{dashboard_url}/api/v1/agent/uploads/approved"
            headers = {"X-API-Key": api_key}
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)
                if response.status_code == 200:
                    hashes = response.json().get('approved_hashes', [])
                    old_count = len(self._approved_hashes)
                    self._approved_hashes = set(hashes)
                    
                    if len(self._approved_hashes) != old_count:
                        self.logger.info(f"Synced {len(hashes)} approved file hashes")
                        # If we have any approved hashes, temporarily enable dialogs
                        # This allows the user to actually pick the file they requested
                        if self.block_all:
                            should_allow = len(self._approved_hashes) > 0
                            self._registry_manager.set_browser_upload_policy(should_allow)
                            self.logger.info(f"Dynamic Policy: File dialogs {'ENABLED' if should_allow else 'DISABLED'} (based on approvals)")
        except Exception as e:
            self.logger.error(f"Failed to sync approvals: {e}")

    def _is_file_approved(self, payload: bytes) -> bool:
        """
        Attempt to identify if the file being uploaded is approved.
        This is complex due to multipart/form-data encoding.
        For now, we use a volume-based approach but allow whitelisted IPs/Domains.
        """
        # PER-FILE APPROVAL LOGIC:
        # In a real DLP, we would proxy the traffic, reconstruct the file,
        # and check the hash. For this agent, we will allow the upload
        # if the destination is whitelisted or if we've received an approval
        # signal from the dashboard for a 'general bypass' window.
        return False
        
    def _enforce_lockdown(self, force_kill: bool = True):
        """Apply surgical action-based lockdown measures."""
        self.logger.info(f"DLP STATE REFRESH: BlockAll={self.block_all}, Approvals={len(self._approved_hashes)}")
        
        # 1. Kill Browsers ONLY if transitioning state or requested
        if force_kill:
            self.logger.warning("Refreshing browser security state...")
            browser_exes = ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"]
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'].lower() in browser_exes:
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        # 2. FORCE CLEANUP of all previous aggressive blocks
        if self._firewall_manager:
            self._firewall_manager.clear_browser_locks()
            self._firewall_manager.unblock_domain("Global_Block_80")
            self._firewall_manager.unblock_domain("Global_Block_443")
        
        if self._registry_manager:
            self._registry_manager.set_system_proxy_lockdown(False)
            self._registry_manager.apply_url_blocklist([])
            
        # 3. Apply the SURGICAL 'Open File' window block
        if self._registry_manager:
            should_allow_picker = (not self.block_all) or (len(self._approved_hashes) > 0)
            self._registry_manager.set_browser_upload_policy(should_allow_picker)
        
        # 4. Flush DNS and refresh system settings
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
        self.logger.info("DLP security refresh complete.")

    def _window_monitor_loop(self):
        """
        Active window monitoring to close file picker dialogs.
        This provides immediate surgical blocking of the 'Upload' action.
        """
        import win32gui
        import win32con
        
        while self._running:
            try:
                # Only monitor if blocking is ON and no files are approved
                if self.block_all and len(self._approved_hashes) == 0:
                    # Windows common file dialog titles
                    target_titles = ["Open", "Select File", "Select files", "Upload files", "Choose File", "Open File"]
                    
                    def enum_windows_callback(hwnd, _):
                        if not win32gui.IsWindowVisible(hwnd):
                            return
                        
                        title = win32gui.GetWindowText(hwnd)
                        class_name = win32gui.GetClassName(hwnd)
                        
                        # Check for standard Windows File Dialog class or common titles
                        # #32770 is the standard dialog class ID
                        if class_name == "#32770" or any(t in title for t in target_titles):
                            # Verify it belongs to a browser process
                            # (Optional, but safer to block all during lockdown)
                            self.logger.warning(f"Surgical Block: Closing unauthorized file picker: {title}")
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                            
                    win32gui.EnumWindows(enum_windows_callback, None)
            except Exception:
                pass
            time.sleep(0.5) # High-frequency check for surgical response

    def start(self):
        """Start the DLP monitoring thread."""
        if self._running:
            return
            
        self._running = True
        self._enforce_lockdown(force_kill=False)

        import threading
        # 1. Passive Monitor (Logging only now)
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        # 2. Window Monitor (Active surgical blocking)
        if sys.platform == 'win32':
            self._win_thread = threading.Thread(target=self._window_monitor_loop, daemon=True)
            self._win_thread.start()
            
        self.logger.info("Surgical DLP Guard started")

    def set_config(self, block_all: bool, whitelist: List[str]):
        """Update guard configuration."""
        old_block = self.block_all
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))
        
        # Only kill browsers if the block state actually changed
        if old_block != self.block_all:
            self._enforce_lockdown(force_kill=True)
        else:
            # Periodic refresh without killing browsers
            self._enforce_lockdown(force_kill=False)
            
        self.logger.info(f"DLP Guard synchronized: Block is {'ON' if block_all else 'OFF'}")


    def update_approvals(self, dashboard_url: str, api_key: str):
        """Manually trigger an approval sync."""
        self._sync_approved_hashes(dashboard_url, api_key)

    def stop(self):
        self._running = False
        
        # Restore browser policies on stop
        if self._registry_manager:
            self._registry_manager.set_browser_upload_policy(True)
            
        if self._thread:
            self._thread.join(timeout=2)
        self.logger.info("DLP Guard stopped")
