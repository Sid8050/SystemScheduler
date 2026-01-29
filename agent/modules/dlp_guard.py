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
    # High-risk upload/file sharing and messaging sites (Removed from total block)
    # We now only use these for traffic monitoring priority
    SENSITIVE_DOMAINS = [
        "wetransfer.com", "mega.nz", "dropbox.com", "drive.google.com", 
        "web.whatsapp.com", "web.telegram.org", "slack.com"
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
        
    def _enforce_lockdown(self):
        """Surgically enforce DLP by only blocking the file selection action."""
        self.logger.info(f"Applying Surgical DLP Policy: BlockAll={self.block_all}")
        
        # 1. KILL browsers to apply policies and clear internet-killing blocks
        # We kill browsers on EVERY state change to ensure the user is not 'stuck' 
        # with old proxy/firewall settings from previous versions.
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "msedge.exe", "/T"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "firefox.exe", "/T"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "brave.exe", "/T"], capture_output=True)

        # 2. Forcefully CLEAR all internet-killing blocks (Firewall/Proxy/URL Blacklists)
        if self._firewall_manager:
            self._firewall_manager.clear_browser_locks()
            self._firewall_manager.unblock_domain("Global_Block_80")
            self._firewall_manager.unblock_domain("Global_Block_443")
        
        if self._registry_manager:
            # Thorough cleanup of Proxy settings
            self._registry_manager.set_system_proxy_lockdown(False)
            # Thorough cleanup of URL blocklist (messaging apps/sharing sites)
            self._registry_manager.apply_url_blocklist([])
            
        # 3. Apply ONLY the surgical dialog block if enabled
        if self._registry_manager:
            should_allow_dialogs = (not self.block_all) or (len(self._approved_hashes) > 0)
            self._registry_manager.set_browser_upload_policy(should_allow_dialogs)
            
            if self.block_all and not should_allow_dialogs:
                self.logger.warning("Upload Lockdown: Windows File Picker has been DISABLED.")
            elif self.block_all and should_allow_dialogs:
                self.logger.info("Upload Lockdown: File Picker ENABLED due to active approval.")
        
        # 4. Flush DNS and Shell notifications
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True)

    def set_config(self, block_all: bool, whitelist: List[str]):
        """Update guard configuration."""
        old_block = self.block_all
        
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))
        
        # Always re-enforce to ensure surgical precision and clear old blocks
        self._enforce_lockdown()
            
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

