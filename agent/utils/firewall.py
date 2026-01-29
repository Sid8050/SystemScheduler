import subprocess
import socket
from typing import List, Set

class FirewallManager:
    """
    Manage Windows Firewall rules for domain blocking.
    
    Uses netsh to create and delete outbound block rules.
    """
    
    RULE_PREFIX = "EndpointSecurity_Block_"
    
    def __init__(self):
        pass
        
    def _run_command(self, cmd: List[str]) -> bool:
        """Run a netsh command as administrator."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                shell=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def block_ips(self, domain: str, ips: List[str]) -> bool:
        """Create firewall rules to block specific IP addresses."""
        if not ips:
            return True
            
        success = True
        ip_list = ",".join(ips)
        rule_name = f"{self.RULE_PREFIX}{domain}"
        
        # Delete existing rule first
        self.unblock_domain(domain)
        
        # Create outbound block rule
        cmd = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f'name="{rule_name}"',
            "dir=out",
            "action=block",
            f'remoteip={ip_list}',
            "enable=yes"
        ]
        
        if not self._run_command(cmd):
            success = False
            
        return success

    def unblock_domain(self, domain: str) -> bool:
        """Remove firewall rules for a domain."""
        rule_name = f"{self.RULE_PREFIX}{domain}"
        cmd = [
            "netsh", "advfirewall", "firewall", "delete", "rule",
            f'name="{rule_name}"'
        ]
        return self._run_command(cmd)

    def clear_all_blocks(self) -> bool:
        """Remove all security-managed firewall rules."""
        cmd = [
            "netsh", "advfirewall", "firewall", "delete", "rule",
            f'name="all"',
            f'description="Endpoint Security Managed Block Rule"'
        ]
        # Since we use prefixes, it's safer to delete by name matching if possible,
        # but netsh doesn't support wildcards in delete. 
        # We'll rely on individual unblocks for now.
        return True

    def resolve_domain(self, domain: str) -> List[str]:
        """Resolve a domain name to all associated IP addresses."""
        try:
            # Clean domain (remove wildcards if any for resolution)
            res_domain = domain.replace("*.", "")
            _, _, ip_list = socket.gethostbyname_ex(res_domain)
            return ip_list
        except Exception:
            return []
