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

    def block_browser_outbound(self, browser_name: str) -> bool:
        rule_name = f"{self.RULE_PREFIX}BrowserLock_{browser_name}"
        cmd = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f'name="{rule_name}"',
            "dir=out",
            "action=block",
            f'program="{browser_name}"',
            "enable=yes"
        ]
        return self._run_command(cmd)

    def allow_domain_for_browser(self, domain: str, ips: List[str]) -> bool:
        if not ips: return True
        ip_list = ",".join(ips)
        rule_name = f"{self.RULE_PREFIX}Allow_{domain}"
        
        cmd = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f'name="{rule_name}"',
            "dir=out",
            "action=allow",
            f'remoteip={ip_list}',
            "enable=yes"
        ]
        return self._run_command(cmd)

    def clear_browser_locks(self) -> bool:
        ps_cmd = f'Get-NetFirewallRule -DisplayName "{self.RULE_PREFIX}*" | Remove-NetFirewallRule'
        try:
            subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
            return True
        except Exception:
            return False

    def resolve_domain(self, domain: str) -> List[str]:
        ips = set()
        try:
            res_domain = domain.replace("*.", "")
            
            try:
                _, _, ip_list = socket.gethostbyname_ex(res_domain)
                ips.update(ip_list)
            except Exception:
                pass
                
            common_subs = ['www', 'mail', 'api', 'm', 'dev', 'static']
            for sub in common_subs:
                try:
                    _, _, ip_list = socket.gethostbyname_ex(f"{sub}.{res_domain}")
                    ips.update(ip_list)
                except Exception:
                    pass
        except Exception:
            pass
        return list(ips)
