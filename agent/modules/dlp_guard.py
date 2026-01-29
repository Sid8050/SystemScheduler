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
    # High-risk upload/file sharing and messaging sites
    UPLOAD_SITE_BLACKLIST = [
        "wetransfer.com", "mega.nz", "dropbox.com", "drive.google.com", 
        "mediafire.com", "4shared.com", "zippyshare.com", "rapidgator.net",
        "sendspace.com", "transfer.pcloud.com", "file.io", "gofile.io",
        "transfer.sh", "wormhole.app", "smash.com", "docsend.com",
        "scribd.com", "issuu.com", "box.com", "icloud.com", "onedrive.live.com",
        "web.whatsapp.com", "web.telegram.org", "discord.com", "slack.com",
        "messenger.com", "facebook.com/messages"
    ]
    
    # Desktop apps that allow file transfer
    PROCESS_BLACKLIST = [
        "WhatsApp.exe", "Telegram.exe", "OneDrive.exe", "Dropbox.exe",
        "Box.exe", "Slack.exe", "Discord.exe"
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
        self.logger.info(f"Enforcing DLP State: BlockAll={self.block_all}")
        
        # 1. Kill blacklisted processes
        if self.block_all:
            for proc in self.PROCESS_BLACKLIST:
                subprocess.run(["taskkill", "/F", "/IM", proc, "/T"], capture_output=True)
        
        # 2. Clean up previous firewall/proxy blocks
        if self._firewall_manager:
            self._firewall_manager.clear_browser_locks()
        
        if self._registry_manager:
            self._registry_manager.set_system_proxy_lockdown(False)
            
        # 3. If Block is OFF, we are done
        if not self.block_all:
            if self._registry_manager:
                self._registry_manager.set_browser_upload_policy(True)
                self._registry_manager.apply_url_blocklist([])
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
            return

        # 4. If Block is ON, apply surgical restrictions
        self.logger.warning("Enforcing Surgical Upload Lockdown...")
        
        # Kill browsers to force policy reload
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "msedge.exe", "/T"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "firefox.exe", "/T"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "brave.exe", "/T"], capture_output=True)
        
        if self._registry_manager:
            # surgical Browser Policy (Kills dialogs and drag-drop)
            self._registry_manager.set_browser_upload_policy(False)
            
            # URL Blocklist (Messaging + File Sharing)
            active_blacklist = [d for d in self.UPLOAD_SITE_BLACKLIST if d not in self.whitelist]
            self._registry_manager.apply_url_blocklist(active_blacklist)
            
        # Flush DNS
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True)

    def set_config(self, block_all: bool, whitelist: List[str]):
        """Update guard configuration."""
        # Detect if we are changing state or whitelist
        old_block = self.block_all
        old_whitelist = self.whitelist
        
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))
        
        # If toggled ON, or whitelist changed while ON, re-enforce
        if (block_all and not old_block) or (block_all and self.whitelist != old_whitelist):
            self._enforce_lockdown()
        # If toggled OFF, clear everything
        elif not block_all and old_block:
            self._enforce_lockdown() # This now handles cleanup
            
        self.logger.info(f"DLP Guard synchronized: Block is {'ON' if block_all else 'OFF'}")



    def stop(self):
        self._running = False
        
        # Restore browser policies on stop
        if self._registry_manager:
            self._registry_manager.set_browser_upload_policy(True)
            
        if self._thread:
            self._thread.join(timeout=2)
        self.logger.info("DLP Guard stopped")

