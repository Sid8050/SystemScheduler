"""
Network Guard Module for Endpoint Security Agent

Provides:
- Website blocking via hosts file or DNS proxy
- Network connection monitoring
- Bandwidth tracking per process
- DNS query logging
"""

import os
import sys
import socket
import struct
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.registry import get_registry_manager
from utils.firewall import FirewallManager

# Windows-specific imports
if sys.platform == 'win32':
    import psutil
else:
    psutil = None


class BlockingMethod(str, Enum):
    """Website blocking methods."""
    HOSTS = "hosts"         # Modify hosts file
    DNS_PROXY = "dns_proxy" # Local DNS proxy
    # WFP = "wfp"           # Windows Filtering Platform (requires driver)


@dataclass
class BlockedCategory:
    """Category of blocked websites."""
    name: str
    domains: List[str]


# Default blocked categories
DEFAULT_CATEGORIES = {
    'social_media': BlockedCategory('Social Media', [
        'facebook.com', 'www.facebook.com', 'fbcdn.net',
        'twitter.com', 'www.twitter.com', 'x.com', 'www.x.com',
        'instagram.com', 'www.instagram.com',
        'tiktok.com', 'www.tiktok.com',
        'reddit.com', 'www.reddit.com',
        'pinterest.com', 'www.pinterest.com',
        'snapchat.com', 'www.snapchat.com',
    ]),
    'gambling': BlockedCategory('Gambling', [
        'bet365.com', 'pokerstars.com', 'draftkings.com',
        'fanduel.com', 'bovada.lv', 'betway.com',
    ]),
    'adult': BlockedCategory('Adult Content', [
        # Left intentionally minimal - can be configured
    ]),
    'streaming': BlockedCategory('Streaming', [
        'netflix.com', 'www.netflix.com',
        'hulu.com', 'www.hulu.com',
        'disneyplus.com', 'www.disneyplus.com',
        'twitch.tv', 'www.twitch.tv',
    ]),
    'gaming': BlockedCategory('Gaming', [
        'steampowered.com', 'store.steampowered.com',
        'epicgames.com', 'www.epicgames.com',
        'ea.com', 'www.ea.com',
    ]),
}


@dataclass
class NetworkConnection:
    """Information about a network connection."""
    timestamp: datetime
    process_name: str
    process_id: int
    local_address: str
    local_port: int
    remote_address: str
    remote_port: int
    status: str
    protocol: str = "tcp"


@dataclass
class DNSQuery:
    """DNS query information."""
    timestamp: datetime
    domain: str
    query_type: str
    response_ip: Optional[str]
    blocked: bool = False


@dataclass
class ProcessBandwidth:
    """Bandwidth usage for a process."""
    process_name: str
    process_id: int
    bytes_sent: int = 0
    bytes_recv: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class HostsFileManager:
    """
    Manage website blocking via hosts file.
    """
    
    HOSTS_PATH = Path("C:/Windows/System32/drivers/etc/hosts")
    MARKER_START = "# === ENDPOINT SECURITY AGENT - DO NOT EDIT ==="
    MARKER_END = "# === END ENDPOINT SECURITY AGENT ==="
    
    def __init__(self):
        self._original_content: Optional[str] = None
        self._blocked_domains: Set[str] = set()
    
    def _read_hosts(self) -> str:
        """Read current hosts file content."""
        try:
            return self.HOSTS_PATH.read_text(encoding='utf-8')
        except Exception:
            return ""
    
    def _write_hosts(self, content: str) -> bool:
        """Write to hosts file (requires admin)."""
        try:
            self.HOSTS_PATH.write_text(content, encoding='utf-8')
            return True
        except PermissionError:
            print("Error: Admin privileges required to modify hosts file")
            return False
        except Exception as e:
            print(f"Error writing hosts file: {e}")
            return False
    
    def _get_block_entries(self) -> str:
        if not self._blocked_domains:
            return ""
        
        lines = [self.MARKER_START]
        common_subs = ['www', 'm', 'api', 'mail', 'static', 'dev']
        
        for domain in sorted(self._blocked_domains):
            lines.append(f"127.0.0.1 {domain}")
            lines.append(f"::1 {domain}")
            
            if not any(domain.startswith(sub + '.') for sub in common_subs):
                for sub in common_subs:
                    lines.append(f"127.0.0.1 {sub}.{domain}")
                    lines.append(f"::1 {sub}.{domain}")
                    
        lines.append(self.MARKER_END)
        
        return '\n'.join(lines)
    
    def add_blocked_domains(self, domains: List[str]):
        """Add domains to block list."""
        for domain in domains:
            # Handle wildcards
            if domain.startswith('*.'):
                domain = domain[2:]
            self._blocked_domains.add(domain.lower())
    
    def remove_blocked_domains(self, domains: List[str]):
        """Remove domains from block list."""
        for domain in domains:
            self._blocked_domains.discard(domain.lower())
    
    def apply_blocks(self) -> bool:
        """Apply current block list to hosts file."""
        content = self._read_hosts()
        
        # Remove existing blocks
        lines = content.split('\n')
        new_lines = []
        in_block = False
        
        for line in lines:
            if self.MARKER_START in line:
                in_block = True
                continue
            if self.MARKER_END in line:
                in_block = False
                continue
            if not in_block:
                new_lines.append(line)
        
        # Add new blocks
        block_entries = self._get_block_entries()
        if block_entries:
            new_lines.append('')
            new_lines.append(block_entries)
        
        new_content = '\n'.join(new_lines)
        
        if self._write_hosts(new_content):
            # Flush DNS cache
            os.system('ipconfig /flushdns > nul 2>&1')
            return True
        return False
    
    def clear_blocks(self) -> bool:
        """Remove all blocks from hosts file."""
        content = self._read_hosts()
        
        # Remove our blocks
        lines = content.split('\n')
        new_lines = []
        in_block = False
        
        for line in lines:
            if self.MARKER_START in line:
                in_block = True
                continue
            if self.MARKER_END in line:
                in_block = False
                continue
            if not in_block:
                new_lines.append(line)
        
        new_content = '\n'.join(new_lines)
        self._blocked_domains.clear()
        
        if self._write_hosts(new_content):
            os.system('ipconfig /flushdns > nul 2>&1')
            return True
        return False
    
    def is_domain_blocked(self, domain: str) -> bool:
        """Check if a domain is currently blocked."""
        domain_lower = domain.lower()
        
        # Check exact match
        if domain_lower in self._blocked_domains:
            return True
        
        # Check if parent domain is blocked
        parts = domain_lower.split('.')
        for i in range(len(parts)):
            parent = '.'.join(parts[i:])
            if parent in self._blocked_domains:
                return True
        
        return False


class DNSProxy:
    """
    Simple DNS proxy for domain blocking and logging.
    
    Intercepts DNS queries and blocks configured domains.
    """
    
    def __init__(
        self,
        blocked_domains: Set[str],
        upstream_dns: str = "8.8.8.8",
        listen_port: int = 53,
        on_query: Optional[Callable[[DNSQuery], None]] = None
    ):
        self.blocked_domains = blocked_domains
        self.upstream_dns = upstream_dns
        self.listen_port = listen_port
        self.on_query = on_query
        
        self._running = False
        self._socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
    
    def _parse_dns_query(self, data: bytes) -> Tuple[str, str]:
        """Parse DNS query to extract domain name and query type."""
        # Skip header (12 bytes)
        offset = 12
        domain_parts = []
        
        while True:
            length = data[offset]
            if length == 0:
                break
            offset += 1
            domain_parts.append(data[offset:offset + length].decode('ascii', errors='ignore'))
            offset += length
        
        domain = '.'.join(domain_parts)
        
        # Get query type
        offset += 1
        qtype = struct.unpack('>H', data[offset:offset + 2])[0]
        query_type = {1: 'A', 28: 'AAAA', 5: 'CNAME', 15: 'MX'}.get(qtype, str(qtype))
        
        return domain, query_type
    
    def _create_nxdomain_response(self, query: bytes) -> bytes:
        """Create NXDOMAIN response for blocked domain."""
        # Copy transaction ID
        response = bytearray(query[:2])
        
        # Flags: Standard response, NXDOMAIN
        response.extend([0x81, 0x83])
        
        # Copy question count, set answer count to 0
        response.extend(query[4:6])  # QDCOUNT
        response.extend([0, 0])       # ANCOUNT
        response.extend([0, 0])       # NSCOUNT
        response.extend([0, 0])       # ARCOUNT
        
        # Copy question section
        offset = 12
        while query[offset] != 0:
            offset += query[offset] + 1
        offset += 5  # null byte + type + class
        
        response.extend(query[12:offset])
        
        return bytes(response)
    
    def _is_blocked(self, domain: str) -> bool:
        """Check if domain should be blocked."""
        domain_lower = domain.lower()
        
        for blocked in self.blocked_domains:
            if blocked.startswith('*.'):
                # Wildcard match
                suffix = blocked[1:]  # Remove *
                if domain_lower.endswith(suffix) or domain_lower == suffix[1:]:
                    return True
            else:
                # Exact match or subdomain
                if domain_lower == blocked or domain_lower.endswith('.' + blocked):
                    return True
        
        return False
    
    def _handle_query(self, data: bytes, addr: Tuple[str, int]):
        """Handle a DNS query."""
        try:
            domain, query_type = self._parse_dns_query(data)
            
            blocked = self._is_blocked(domain)
            
            # Log query
            query_info = DNSQuery(
                timestamp=datetime.now(),
                domain=domain,
                query_type=query_type,
                response_ip=None,
                blocked=blocked
            )
            
            if self.on_query:
                self.on_query(query_info)
            
            if blocked:
                # Send NXDOMAIN response
                response = self._create_nxdomain_response(data)
                self._socket.sendto(response, addr)
            else:
                # Forward to upstream DNS
                upstream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                upstream_socket.settimeout(5)
                
                try:
                    upstream_socket.sendto(data, (self.upstream_dns, 53))
                    response, _ = upstream_socket.recvfrom(4096)
                    self._socket.sendto(response, addr)
                finally:
                    upstream_socket.close()
        
        except Exception as e:
            print(f"DNS proxy error: {e}")
    
    def _run(self):
        """Main DNS proxy loop."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(('127.0.0.1', self.listen_port))
        self._socket.settimeout(1)
        
        while self._running:
            try:
                data, addr = self._socket.recvfrom(4096)
                # Handle in thread to not block
                threading.Thread(
                    target=self._handle_query,
                    args=(data, addr),
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    print(f"DNS proxy error: {e}")
        
        self._socket.close()
    
    def start(self):
        """Start DNS proxy."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop DNS proxy."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)


class NetworkGuard:
    """
    Network monitoring and website blocking.
    """
    
    def __init__(
        self,
        blocking_method: BlockingMethod = BlockingMethod.HOSTS,
        blocked_sites: Optional[List[str]] = None,
        blocked_categories: Optional[List[str]] = None,
        allowed_sites: Optional[List[str]] = None,
        log_connections: bool = True,
        log_dns: bool = True,
        track_bandwidth: bool = True,
        on_blocked: Optional[Callable[[str, str], None]] = None,
        on_connection: Optional[Callable[[NetworkConnection], None]] = None,
        on_dns_query: Optional[Callable[[DNSQuery], None]] = None
    ):
        self.blocking_method = blocking_method
        self.allowed_sites = set(s.lower() for s in (allowed_sites or []))
        self.log_connections = log_connections
        self.log_dns = log_dns
        self.track_bandwidth = track_bandwidth
        
        # Callbacks
        self.on_blocked = on_blocked
        self.on_connection = on_connection
        self.on_dns_query = on_dns_query
        
        # Build blocked domains set
        self._blocked_domains: Set[str] = set()
        
        # Add explicitly blocked sites
        for site in (blocked_sites or []):
            self._blocked_domains.add(site.lower())
        
        # Add category-based blocks
        for category in (blocked_categories or []):
            if category in DEFAULT_CATEGORIES:
                for domain in DEFAULT_CATEGORIES[category].domains:
                    self._blocked_domains.add(domain.lower())
        
        # Remove allowed sites
        self._blocked_domains -= self.allowed_sites
        
        # Blocking implementations
        self._hosts_manager: Optional[HostsFileManager] = None
        self._dns_proxy: Optional[DNSProxy] = None
        self._firewall_manager: Optional[FirewallManager] = None
        self._registry_manager = get_registry_manager()
        
        # Monitoring state
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._resolver_thread: Optional[threading.Thread] = None
        self._connections: List[NetworkConnection] = []
        self._bandwidth: Dict[int, ProcessBandwidth] = {}
        self._connections_lock = threading.Lock()
    
    def _setup_blocking(self):
        if self._registry_manager:
            self._registry_manager.disable_browser_doh()
            
        if sys.platform == 'win32':
            self._firewall_manager = FirewallManager()
            
        if self.blocking_method == BlockingMethod.HOSTS:
            self._hosts_manager = HostsFileManager()
            self._hosts_manager.add_blocked_domains(list(self._blocked_domains))
            self._hosts_manager.apply_blocks()
            
            if self._firewall_manager:
                self._update_firewall_rules()
        
        elif self.blocking_method == BlockingMethod.DNS_PROXY:
            self._dns_proxy = DNSProxy(
                blocked_domains=self._blocked_domains,
                on_query=self._handle_dns_query
            )
            self._dns_proxy.start()
            
    def _update_firewall_rules(self):
        if not self._firewall_manager:
            return
            
        for domain in self._blocked_domains:
            ips = self._firewall_manager.resolve_domain(domain)
            if ips:
                self._firewall_manager.block_ips(domain, ips)
    
    def _resolver_loop(self):
        while self._running:
            try:
                self._update_firewall_rules()
            except Exception:
                pass
            for _ in range(1800):
                if not self._running:
                    break
                time.sleep(1)
    
    def _teardown_blocking(self):
        if self._hosts_manager:
            self._hosts_manager.clear_blocks()
            self._hosts_manager = None
            
        if self._firewall_manager:
            for domain in self._blocked_domains:
                self._firewall_manager.unblock_domain(domain)
            self._firewall_manager = None
        
        if self._dns_proxy:
            self._dns_proxy.stop()
            self._dns_proxy = None
    
    def _handle_dns_query(self, query: DNSQuery):
        """Handle DNS query callback."""
        if query.blocked and self.on_blocked:
            self.on_blocked(query.domain, "DNS query blocked")
        
        if self.on_dns_query:
            self.on_dns_query(query)
    
    def _get_connections(self) -> List[NetworkConnection]:
        """Get current network connections."""
        connections = []
        
        if psutil is None:
            return connections
        
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'NONE':
                    continue
                
                # Get process info
                process_name = "Unknown"
                if conn.pid:
                    try:
                        process = psutil.Process(conn.pid)
                        process_name = process.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Parse addresses
                local_addr = conn.laddr.ip if conn.laddr else ""
                local_port = conn.laddr.port if conn.laddr else 0
                remote_addr = conn.raddr.ip if conn.raddr else ""
                remote_port = conn.raddr.port if conn.raddr else 0
                
                connections.append(NetworkConnection(
                    timestamp=datetime.now(),
                    process_name=process_name,
                    process_id=conn.pid or 0,
                    local_address=local_addr,
                    local_port=local_port,
                    remote_address=remote_addr,
                    remote_port=remote_port,
                    status=conn.status,
                    protocol="tcp" if conn.type == socket.SOCK_STREAM else "udp"
                ))
        
        except Exception as e:
            print(f"Error getting connections: {e}")
        
        return connections
    
    def _update_bandwidth(self):
        """Update bandwidth tracking."""
        if psutil is None:
            return
        
        try:
            # Get network IO per process
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    io = proc.io_counters()
                    pid = proc.info['pid']
                    
                    if pid in self._bandwidth:
                        bw = self._bandwidth[pid]
                        bw.bytes_sent = io.write_bytes
                        bw.bytes_recv = io.read_bytes
                        bw.last_update = datetime.now()
                    else:
                        self._bandwidth[pid] = ProcessBandwidth(
                            process_name=proc.info['name'],
                            process_id=pid,
                            bytes_sent=io.write_bytes,
                            bytes_recv=io.read_bytes
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                # Get connections
                if self.log_connections:
                    connections = self._get_connections()
                    
                    with self._connections_lock:
                        # Find new connections
                        existing_keys = {
                            (c.remote_address, c.remote_port, c.process_id)
                            for c in self._connections
                        }
                        
                        for conn in connections:
                            key = (conn.remote_address, conn.remote_port, conn.process_id)
                            if key not in existing_keys and conn.status == 'ESTABLISHED':
                                self._connections.append(conn)
                                if self.on_connection:
                                    self.on_connection(conn)
                        
                        # Keep last 1000 connections
                        if len(self._connections) > 1000:
                            self._connections = self._connections[-1000:]
                
                # Update bandwidth
                if self.track_bandwidth:
                    self._update_bandwidth()
                
            except Exception as e:
                print(f"Monitor error: {e}")
            
            time.sleep(5)  # Check every 5 seconds
    
    def start(self):
        """Start network guard."""
        if self._running:
            return
        
        self._running = True
        
        # Setup blocking
        self._setup_blocking()
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        self._resolver_thread = threading.Thread(target=self._resolver_loop, daemon=True)
        self._resolver_thread.start()
    
    def stop(self):
        """Stop network guard."""
        self._running = False
        
        # Stop monitoring
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            
        if self._resolver_thread:
            self._resolver_thread.join(timeout=5)
        
        # Remove blocking
        self._teardown_blocking()
    
    def add_blocked_site(self, domain: str):
        """Add a site to block list."""
        domain_lower = domain.lower()
        self._blocked_domains.add(domain_lower)
        
        if self._hosts_manager:
            self._hosts_manager.add_blocked_domains([domain_lower])
            self._hosts_manager.apply_blocks()
            
        if self._firewall_manager:
            ips = self._firewall_manager.resolve_domain(domain_lower)
            if ips:
                self._firewall_manager.block_ips(domain_lower, ips)
    
    def remove_blocked_site(self, domain: str):
        """Remove a site from block list."""
        domain_lower = domain.lower()
        self._blocked_domains.discard(domain_lower)
        
        if self._hosts_manager:
            self._hosts_manager.remove_blocked_domains([domain_lower])
            self._hosts_manager.apply_blocks()
            
        if self._firewall_manager:
            self._firewall_manager.unblock_domain(domain_lower)
    
    def is_site_blocked(self, domain: str) -> bool:
        """Check if a site is blocked."""
        if self._hosts_manager:
            return self._hosts_manager.is_domain_blocked(domain)
        return domain.lower() in self._blocked_domains
    
    def get_recent_connections(self, limit: int = 100) -> List[NetworkConnection]:
        """Get recent network connections."""
        with self._connections_lock:
            return self._connections[-limit:]
    
    def get_bandwidth_stats(self) -> Dict[str, ProcessBandwidth]:
        """Get bandwidth statistics per process."""
        return {
            bw.process_name: bw
            for bw in self._bandwidth.values()
        }
    
    def get_blocked_domains(self) -> List[str]:
        """Get list of blocked domains."""
        return sorted(self._blocked_domains)
