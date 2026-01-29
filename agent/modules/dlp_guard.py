import pydivert
import socket
import re
import sys
from typing import List, Set, Optional
from datetime import datetime
from agent.core.logger import Logger
from agent.utils.registry import get_registry_manager

class DataLossGuard:
    def __init__(self, logger: Logger, block_all: bool = False, whitelist: List[str] = None):
        self.logger = logger
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))
        self._running = False
        self._thread = None
        self._approved_hashes = set()
        self._approved_destinations = set()
        self._registry_manager = get_registry_manager()
        
    def set_config(self, block_all: bool, whitelist: List[str]):
        """Update guard configuration."""
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))
        
        # Enforce browser policies
        if self._registry_manager:
            self._registry_manager.set_browser_upload_policy(not block_all)
            
        self.logger.info(f"DLP Guard config updated: block_all={block_all}, whitelist_count={len(self.whitelist)}")

    def _extract_host(self, payload: bytes) -> Optional[str]:
        try:
            match = re.search(b"Host: ([^\r\n]+)", payload)
            if match:
                return match.group(1).decode('utf-8').strip()
        except Exception:
            pass
        return None

    def _is_post_request(self, payload: bytes) -> bool:
        return payload.startswith(b"POST ")

    def _monitor_loop(self):
        filter_str = "tcp.DstPort == 80 or tcp.DstPort == 443 and tcp.PayloadLength > 0"
        
        try:
            with pydivert.WinDivert(filter_str) as w:
                for packet in w:
                    if not self._running:
                        break
                        
                    payload = packet.payload
                    
                    # Packet level blocking (best effort for HTTP)
                    if self.block_all and self._is_post_request(payload):
                        host = self._extract_host(payload)
                        is_whitelisted = False
                        if host:
                            host_lower = host.lower()
                            if host_lower in self.whitelist or host_lower in self._approved_destinations:
                                is_whitelisted = True
                            else:
                                for w_domain in self.whitelist:
                                    if host_lower.endswith('.' + w_domain):
                                        is_whitelisted = True
                                        break
                        
                        if not is_whitelisted:
                            self.logger.warning(f"Blocked unauthorized upload attempt to: {host or 'Unknown Host'}")
                            continue
                            
                    w.send(packet)
                    
        except Exception as e:
            self.logger.error(f"DLP Guard monitor error: {e}")
            self._running = False

    def start(self):
        if self._running:
            return
            
        # Initial policy enforcement
        if self._registry_manager:
            self._registry_manager.set_browser_upload_policy(not self.block_all)

        if not self.block_all:
            return
            
        import threading
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.logger.info("DLP Guard started (Upload Blocking Active)")

    def stop(self):
        self._running = False
        
        # Restore browser policies on stop
        if self._registry_manager:
            self._registry_manager.set_browser_upload_policy(True)
            
        if self._thread:
            self._thread.join(timeout=2)
        self.logger.info("DLP Guard stopped")

