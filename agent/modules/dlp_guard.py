import pydivert
import socket
import re
import sys
import subprocess
import shutil
from typing import List, Set, Optional
from datetime import datetime
from agent.core.logger import Logger
from agent.utils.registry import get_registry_manager
from agent.utils.firewall import FirewallManager

class DataLossGuard:
    # High-risk upload/file sharing sites to block when DLP is enabled
    UPLOAD_SITE_BLACKLIST = [
        "wetransfer.com", "mega.nz", "dropbox.com", "drive.google.com", 
        "mediafire.com", "4shared.com", "zippyshare.com", "rapidgator.net",
        "sendspace.com", "transfer.pcloud.com", "file.io", "gofile.io",
        "transfer.sh", "wormhole.app", "smash.com", "docsend.com",
        "scribd.com", "issuu.com", "box.com", "icloud.com", "onedrive.live.com"
    ]

    def __init__(self, logger: Logger, block_all: bool = False, whitelist: List[str] = None):
        self.logger = logger
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))
        self._running = False
        self._thread = None
        self._approved_hashes = set()
        self._approved_destinations = set()
        self._registry_manager = get_registry_manager()
        self._firewall_manager = FirewallManager() if sys.platform == 'win32' else None
        
    def _get_browser_paths(self) -> List[str]:
        """Find common browser executables on Windows."""
        paths = []
        if sys.platform != 'win32': return []
        
        # Check standard locations
        search_dirs = [
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
            os.path.join(os.environ.get("LocalAppData", ""), "Google\\Chrome\\Application"),
        ]
        
        executables = ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"]
        
        for d in search_dirs:
            if not os.path.exists(d): continue
            for exe in executables:
                # Recursive search for the exe
                for root, _, files in os.walk(d):
                    if exe in files:
                        paths.append(os.path.join(root, exe))
        return list(set(paths))

    def start(self):
        if self._running:
            return
            
        # Initial policy enforcement
        self._enforce_lockdown()

        if not self.block_all:
            return
            
        import threading
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.logger.info("DLP Guard started (Upload Blocking Active)")

    def _enforce_lockdown(self):
        """Apply all configured lockdown measures."""
        if self.block_all:
            self.logger.warning("Enforcing Lockdown: Terminating browsers to apply security policies...")
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True)
            subprocess.run(["taskkill", "/F", "/IM", "msedge.exe", "/T"], capture_output=True)
            subprocess.run(["taskkill", "/F", "/IM", "firefox.exe", "/T"], capture_output=True)
            subprocess.run(["taskkill", "/F", "/IM", "brave.exe", "/T"], capture_output=True)
        
        if self._registry_manager:
            # Iron-Clad Proxy Lockdown
            self._registry_manager.set_system_proxy_lockdown(self.block_all, list(self.whitelist))
            
            # Absolute Browser Policy
            self._registry_manager.set_browser_upload_policy(not self.block_all)
            
        # Apply Firewall Lockdown
        if self._firewall_manager:
            self._firewall_manager.clear_browser_locks()
            if self.block_all:
                browsers = self._get_browser_paths()
                for b_path in browsers:
                    self._firewall_manager.block_browser_outbound(b_path)
                
                for domain in self.whitelist:
                    ips = self._firewall_manager.resolve_domain(domain)
                    if ips:
                        self._firewall_manager.allow_domain_for_browser(domain, ips)

    def set_config(self, block_all: bool, whitelist: List[str]):
        """Update guard configuration."""
        # Only trigger re-enforcement if state actually changed
        changed = (self.block_all != block_all) or (self.whitelist != set(s.lower() for s in whitelist))
        
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))
        
        if changed:
            self._enforce_lockdown()
            
        self.logger.info(f"DLP Guard synchronized with Dashboard. Lockdown: {'ACTIVE' if block_all else 'OFF'}")


    def stop(self):
        self._running = False
        
        # Restore browser policies on stop
        if self._registry_manager:
            self._registry_manager.set_browser_upload_policy(True)
            
        if self._thread:
            self._thread.join(timeout=2)
        self.logger.info("DLP Guard stopped")

