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
        self._approved_hashes = {} 
        self._is_temporarily_unlocked = False
        self._unlock_expiry = 0
        
    def _sync_approved_hashes(self, dashboard_url: str, api_key: str):
        """Fetch approved file hashes from dashboard."""
        try:
            url = f"{dashboard_url}/api/v1/agent/uploads/approved"
            headers = {"X-API-Key": api_key}
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)
                if response.status_code == 200:
                    hashes = response.json().get('approved_hashes', [])
                    self._approved_hashes = {h: True for h in hashes}
                    self.logger.info(f"Synced {len(hashes)} approved file hashes")
        except Exception as e:
            self.logger.error(f"Failed to sync approvals: {e}")

    def request_temporary_unlock(self, duration_seconds: int = 30):
        """Allow the file picker to open for a tiny window of time."""
        if not self.block_all: return
        
        self.logger.warning(f"SECURITY: Manual Bypass Triggered. Unlocking file picker for {duration_seconds}s")
        self._is_temporarily_unlocked = True
        self._unlock_expiry = time.time() + duration_seconds
        
        if self._registry_manager:
            self._registry_manager.set_browser_upload_policy(True)
            
    def _check_unlock_state(self):
        """Check if temporary unlock has expired."""
        if self._is_temporarily_unlocked and time.time() > self._unlock_expiry:
            self.logger.info("Surgical Bypass Expired: Relocking file picker.")
            self._is_temporarily_unlocked = False
            if self._registry_manager:
                self._registry_manager.set_browser_upload_policy(False)

    def _enforce_lockdown(self, force_kill: bool = True):
        """Apply surgical action-based lockdown measures."""
        self.logger.info(f"DLP STATE REFRESH: BlockAll={self.block_all}, Approvals={len(self._approved_hashes)}")
        
        # 1. Aggressive Browser Termination
        if force_kill:
            self.logger.warning("FORCING browser termination to apply security rules...")
            browser_exes = ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"]
            # Try taskkill first (fast)
            for exe in browser_exes:
                subprocess.run(["taskkill", "/F", "/IM", exe, "/T"], capture_output=True)
            
            # Follow up with psutil for any survivors
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'].lower() in browser_exes:
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        # 2. CLEAR internet blocks
        if self._firewall_manager:
            self._firewall_manager.clear_browser_locks()
        
        if self._registry_manager:
            self._registry_manager.set_system_proxy_lockdown(False)
            self._registry_manager.apply_url_blocklist([])
            
        # 3. Apply SURGICAL block
        if self._registry_manager:
            should_allow_picker = (not self.block_all) or (self._is_temporarily_unlocked)
            self._registry_manager.set_browser_upload_policy(should_allow_picker)
            
            if self.block_all:
                status = "ENABLED (Temp Bypass)" if should_allow_picker else "DISABLED"
                self.logger.warning(f"SECURITY POLICY: File selection is {status}")
        
        # 4. Flush
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
        self.logger.info("DLP synchronization complete.")


    def _window_monitor_loop(self):
        """Active window monitoring to close unauthorized file picker dialogs."""
        import win32gui
        import win32con
        
        while self._running:
            try:
                self._check_unlock_state()
                
                # If block is ON and NOT temporarily unlocked
                if self.block_all and not self._is_temporarily_unlocked:
                    target_titles = ["Open", "Select File", "Select files", "Upload files", "Choose File", "Open File"]
                    
                    def enum_windows_callback(hwnd, _):
                        if not win32gui.IsWindowVisible(hwnd):
                            return
                        
                        title = win32gui.GetWindowText(hwnd)
                        class_name = win32gui.GetClassName(hwnd)
                        
                        # Block standard Windows File Dialogs (#32770)
                        if class_name == "#32770" or any(t in title for t in target_titles):
                            self.logger.warning(f"Surgical Block: Terminated unauthorized file picker: {title}")
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                            
                    win32gui.EnumWindows(enum_windows_callback, None)
            except Exception:
                pass
            time.sleep(0.3)

    def _monitor_loop(self):
        """Passive monitor thread."""
        while self._running:
            time.sleep(10)

    def start_guard(self):
        """Start the DLP monitoring threads."""
        if self._running:
            return
            
        self._running = True
        self._enforce_lockdown(force_kill=False)

        import threading
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        if sys.platform == 'win32':
            self._win_thread = threading.Thread(target=self._window_monitor_loop, daemon=True)
            self._win_thread.start()
            
        self.logger.info("Surgical DLP Guard started")

    def set_config(self, block_all: bool, whitelist: List[str]):
        """Update guard configuration."""
        old_block = self.block_all
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))
        
        if old_block != self.block_all:
            self._enforce_lockdown(force_kill=True)
        else:
            self._enforce_lockdown(force_kill=False)
            
        self.logger.info(f"DLP Guard synchronized: Block is {'ON' if block_all else 'OFF'}")

    def update_approvals(self, dashboard_url: str, api_key: str):
        """Manually trigger an approval sync."""
        self._sync_approved_hashes(dashboard_url, api_key)

    def stop(self):
        self._running = False
        if self._registry_manager:
            self._registry_manager.set_browser_upload_policy(True)
        if self._thread:
            self._thread.join(timeout=2)
        self.logger.info("DLP Guard stopped")
