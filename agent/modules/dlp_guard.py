import pydivert
import socket
import re
from typing import List, Set, Optional
from datetime import datetime
from agent.core.logger import Logger

class DataLossGuard:
    """
    Data Loss Prevention (DLP) Guard.
    
    Provides:
    - HTTP POST inspection to block unauthorized file uploads
    - Approval-based upload bypass
    - Domain-based upload whitelisting
    """
    
    def __init__(self, logger: Logger, block_all: bool = False, whitelist: List[str] = None):
        self.logger = logger
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))
        self._running = False
        self._thread = None
        self._approved_hashes = set() # For future per-file approval
        self._approved_destinations = set() # Temporary approvals
        
    def set_config(self, block_all: bool, whitelist: List[str]):
        """Update guard configuration."""
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))
        self.logger.info(f"DLP Guard config updated: block_all={block_all}, whitelist_count={len(self.whitelist)}")

    def _extract_host(self, payload: bytes) -> Optional[str]:
        """Extract the Host header from an HTTP request."""
        try:
            # We look for 'Host: domain.com' in the raw TCP payload
            match = re.search(b"Host: ([^\r\n]+)", payload)
            if match:
                return match.group(1).decode('utf-8').strip()
        except Exception:
            pass
        return None

    def _is_post_request(self, payload: bytes) -> bool:
        """Check if the payload contains an HTTP POST request."""
        return payload.startswith(b"POST ")

    def _monitor_loop(self):
        """Main packet interception loop."""
        # Filter for outbound TCP traffic on common web ports
        # We only look at packets with payloads (tcp.PayloadLength > 0)
        filter_str = "tcp.DstPort == 80 or tcp.DstPort == 443 and tcp.PayloadLength > 0"
        
        try:
            with pydivert.WinDivert(filter_str) as w:
                for packet in w:
                    if not self._running:
                        break
                        
                    payload = packet.payload
                    is_upload = self._is_post_request(payload)
                    
                    if is_upload and self.block_all:
                        host = self._extract_host(payload)
                        
                        # Check if destination is whitelisted
                        is_whitelisted = False
                        if host:
                            host_lower = host.lower()
                            if host_lower in self.whitelist or host_lower in self._approved_destinations:
                                is_whitelisted = True
                            else:
                                # Check for parent domain whitelisting
                                for w_domain in self.whitelist:
                                    if host_lower.endswith('.' + w_domain):
                                        is_whitelisted = True
                                        break
                        
                        if not is_whitelisted:
                            self.logger.warning(f"Blocked unauthorized upload attempt to: {host or 'Unknown Host'}")
                            # To block, we simply don't call w.send(packet)
                            # This drops the POST request.
                            continue
                            
                    # Allow the packet to pass
                    w.send(packet)
                    
        except Exception as e:
            self.logger.error(f"DLP Guard monitor error: {e}")
            self._running = False

    def start(self):
        """Start the DLP monitoring thread."""
        if self._running or not self.block_all:
            return
            
        import threading
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.logger.info("DLP Guard started (Upload Blocking Active)")

    def stop(self):
        """Stop the DLP monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self.logger.info("DLP Guard stopped")
