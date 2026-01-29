"""
Windows Registry Manager for Endpoint Security Agent

Provides safe registry operations for:
- USB device control
- Service management
- Security policies
"""

import sys
from typing import Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

# Windows-specific imports (graceful fallback for non-Windows)
if sys.platform == 'win32':
    import winreg
else:
    # Mock for development on non-Windows
    winreg = None


class RegistryHive(Enum):
    """Registry hive constants."""
    HKEY_LOCAL_MACHINE = "HKLM"
    HKEY_CURRENT_USER = "HKCU"
    HKEY_USERS = "HKU"
    HKEY_CLASSES_ROOT = "HKCR"


class RegistryValueType(Enum):
    """Registry value types."""
    REG_SZ = 1           # String
    REG_EXPAND_SZ = 2    # Expandable string
    REG_BINARY = 3       # Binary
    REG_DWORD = 4        # 32-bit number
    REG_MULTI_SZ = 7     # Multi-string
    REG_QWORD = 11       # 64-bit number


@dataclass
class RegistryValue:
    """Represents a registry value."""
    name: str
    value: Any
    value_type: RegistryValueType


class RegistryManager:
    """
    Safe wrapper for Windows registry operations.
    
    All operations include error handling and logging.
    """
    
    # Common registry paths
    USBSTOR_PATH = r"SYSTEM\CurrentControlSet\Services\USBSTOR"
    REMOVABLE_STORAGE_PATH = r"SOFTWARE\Policies\Microsoft\Windows\RemovableStorageDevices"
    USB_ENUM_PATH = r"SYSTEM\CurrentControlSet\Enum\USBSTOR"
    
    CHROME_POLICY_PATH = r"SOFTWARE\Policies\Google\Chrome"
    EDGE_POLICY_PATH = r"SOFTWARE\Policies\Microsoft\Edge"
    FIREFOX_POLICY_PATH = r"SOFTWARE\Policies\Mozilla\Firefox"

    # Proxy paths
    INTERNET_SETTINGS_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"

    def __init__(self):
        if winreg is None:
            raise RuntimeError("Registry operations only available on Windows")
        
        self._hive_map = {
            RegistryHive.HKEY_LOCAL_MACHINE: winreg.HKEY_LOCAL_MACHINE,
            RegistryHive.HKEY_CURRENT_USER: winreg.HKEY_CURRENT_USER,
            RegistryHive.HKEY_USERS: winreg.HKEY_USERS,
            RegistryHive.HKEY_CLASSES_ROOT: winreg.HKEY_CLASSES_ROOT,
        }
        
        self._type_map = {
            RegistryValueType.REG_SZ: winreg.REG_SZ,
            RegistryValueType.REG_EXPAND_SZ: winreg.REG_EXPAND_SZ,
            RegistryValueType.REG_BINARY: winreg.REG_BINARY,
            RegistryValueType.REG_DWORD: winreg.REG_DWORD,
            RegistryValueType.REG_MULTI_SZ: winreg.REG_MULTI_SZ,
            RegistryValueType.REG_QWORD: winreg.REG_QWORD,
        }
    
    def _get_hive(self, hive: RegistryHive) -> int:
        """Get the Windows registry hive constant."""
        return self._hive_map.get(hive, winreg.HKEY_LOCAL_MACHINE)
    
    def _get_type(self, value_type: RegistryValueType) -> int:
        """Get the Windows registry type constant."""
        return self._type_map.get(value_type, winreg.REG_SZ)
    
    def read_value(
        self,
        hive: RegistryHive,
        path: str,
        name: str
    ) -> Optional[RegistryValue]:
        """
        Read a registry value.
        
        Args:
            hive: Registry hive
            path: Key path
            name: Value name
            
        Returns:
            RegistryValue if found, None otherwise
        """
        try:
            with winreg.OpenKey(self._get_hive(hive), path) as key:
                value, value_type = winreg.QueryValueEx(key, name)
                return RegistryValue(
                    name=name,
                    value=value,
                    value_type=RegistryValueType(value_type)
                )
        except WindowsError:
            return None
    
    def write_value(
        self,
        hive: RegistryHive,
        path: str,
        name: str,
        value: Any,
        value_type: RegistryValueType = RegistryValueType.REG_SZ
    ) -> bool:
        """
        Write a registry value.
        
        Args:
            hive: Registry hive
            path: Key path
            name: Value name
            value: Value to write
            value_type: Type of value
            
        Returns:
            True if successful
        """
        try:
            with winreg.OpenKey(
                self._get_hive(hive),
                path,
                0,
                winreg.KEY_SET_VALUE
            ) as key:
                winreg.SetValueEx(
                    key,
                    name,
                    0,
                    self._get_type(value_type),
                    value
                )
            return True
        except WindowsError as e:
            print(f"Registry write error: {e}")
            return False
    
    def create_key(self, hive: RegistryHive, path: str) -> bool:
        """Create a registry key (and parent keys if needed)."""
        try:
            winreg.CreateKeyEx(self._get_hive(hive), path)
            return True
        except WindowsError as e:
            print(f"Registry create key error: {e}")
            return False
    
    def delete_value(self, hive: RegistryHive, path: str, name: str) -> bool:
        """Delete a registry value."""
        try:
            with winreg.OpenKey(
                self._get_hive(hive),
                path,
                0,
                winreg.KEY_SET_VALUE
            ) as key:
                winreg.DeleteValue(key, name)
            return True
        except WindowsError:
            return False
    
    def key_exists(self, hive: RegistryHive, path: str) -> bool:
        """Check if a registry key exists."""
        try:
            with winreg.OpenKey(self._get_hive(hive), path):
                return True
        except WindowsError:
            return False
    
    def list_subkeys(self, hive: RegistryHive, path: str) -> List[str]:
        """List all subkeys under a registry key."""
        subkeys = []
        try:
            with winreg.OpenKey(self._get_hive(hive), path) as key:
                i = 0
                while True:
                    try:
                        subkey = winreg.EnumKey(key, i)
                        subkeys.append(subkey)
                        i += 1
                    except WindowsError:
                        break
        except WindowsError:
            pass
        return subkeys
    
    def list_values(self, hive: RegistryHive, path: str) -> List[RegistryValue]:
        """List all values under a registry key."""
        values = []
        try:
            with winreg.OpenKey(self._get_hive(hive), path) as key:
                i = 0
                while True:
                    try:
                        name, value, value_type = winreg.EnumValue(key, i)
                        values.append(RegistryValue(
                            name=name,
                            value=value,
                            value_type=RegistryValueType(value_type)
                        ))
                        i += 1
                    except WindowsError:
                        break
        except WindowsError:
            pass
        return values
    
    # USB-specific methods
    def get_usb_storage_state(self) -> bool:
        """
        Check if USB storage is enabled.
        
        Returns:
            True if enabled (Start=3), False if disabled (Start=4)
        """
        value = self.read_value(
            RegistryHive.HKEY_LOCAL_MACHINE,
            self.USBSTOR_PATH,
            "Start"
        )
        if value:
            return value.value == 3
        return True  # Default to enabled
    
    def set_usb_storage_state(self, enabled: bool) -> bool:
        """
        Enable or disable USB storage devices.
        
        Args:
            enabled: True to enable, False to disable
            
        Returns:
            True if successful
        """
        return self.write_value(
            RegistryHive.HKEY_LOCAL_MACHINE,
            self.USBSTOR_PATH,
            "Start",
            3 if enabled else 4,
            RegistryValueType.REG_DWORD
        )
    
    def get_connected_usb_devices(self) -> List[dict]:
        """
        Get list of USB storage devices that have been connected.
        
        Returns:
            List of device info dictionaries
        """
        devices = []
        
        subkeys = self.list_subkeys(
            RegistryHive.HKEY_LOCAL_MACHINE,
            self.USB_ENUM_PATH
        )
        
        for device_class in subkeys:
            device_path = f"{self.USB_ENUM_PATH}\\{device_class}"
            instances = self.list_subkeys(
                RegistryHive.HKEY_LOCAL_MACHINE,
                device_path
            )
            
            for instance in instances:
                instance_path = f"{device_path}\\{instance}"
                
                # Get device info
                friendly_name = self.read_value(
                    RegistryHive.HKEY_LOCAL_MACHINE,
                    instance_path,
                    "FriendlyName"
                )
                
                devices.append({
                    'device_class': device_class,
                    'instance_id': instance,
                    'friendly_name': friendly_name.value if friendly_name else None,
                    'registry_path': instance_path
                })
        
        return devices
    
    def disable_browser_doh(self) -> bool:
        success = True
        
        self.create_key(RegistryHive.HKEY_LOCAL_MACHINE, self.CHROME_POLICY_PATH)
        if not self.write_value(
            RegistryHive.HKEY_LOCAL_MACHINE,
            self.CHROME_POLICY_PATH,
            "DnsOverHttpsMode",
            "off"
        ):
            success = False
            
        self.create_key(RegistryHive.HKEY_LOCAL_MACHINE, self.EDGE_POLICY_PATH)
        if not self.write_value(
            RegistryHive.HKEY_LOCAL_MACHINE,
            self.EDGE_POLICY_PATH,
            "DnsOverHttpsMode",
            "off"
        ):
            success = False
            
        self.create_key(RegistryHive.HKEY_LOCAL_MACHINE, self.FIREFOX_POLICY_PATH)
        if not self.write_value(
            RegistryHive.HKEY_LOCAL_MACHINE,
            self.FIREFOX_POLICY_PATH,
            "DNSOverHTTPS",
            0,
            RegistryValueType.REG_DWORD
        ):
            ff_nested = f"{self.FIREFOX_POLICY_PATH}\\DNSOverHTTPS"
            self.create_key(RegistryHive.HKEY_LOCAL_MACHINE, ff_nested)
            if not self.write_value(
                RegistryHive.HKEY_LOCAL_MACHINE,
                ff_nested,
                "Enabled",
                0,
                RegistryValueType.REG_DWORD
            ):
                success = False
                
        return success

    def set_system_proxy_lockdown(self, enabled: bool, whitelist: List[str] = None) -> bool:
        success = True
        hive = RegistryHive.HKEY_CURRENT_USER
        path = self.INTERNET_SETTINGS_PATH
        
        if enabled:
            self.write_value(hive, path, "ProxyEnable", 1, RegistryValueType.REG_DWORD)
            self.write_value(hive, path, "ProxyServer", "127.0.0.1:9999", RegistryValueType.REG_SZ)
            
            formatted_whitelist = []
            for domain in (whitelist or []):
                if not domain.startswith('*.'):
                    formatted_whitelist.append(f"*.{domain}")
                formatted_whitelist.append(domain)
            
            overrides = ";".join(formatted_whitelist)
            if overrides:
                overrides += ";<local>"
            else:
                overrides = "<local>"
            
            self.write_value(hive, path, "ProxyOverride", overrides, RegistryValueType.REG_SZ)
        else:
            self.write_value(hive, path, "ProxyEnable", 0, RegistryValueType.REG_DWORD)
            
        try:
            import ctypes
            option_settings_changed = 39
            option_refresh = 37
            ctypes.windll.Wininet.InternetSetOptionW(0, option_settings_changed, 0, 0)
            ctypes.windll.Wininet.InternetSetOptionW(0, option_refresh, 0, 0)
        except Exception:
            pass
            
        return success

    def set_browser_upload_policy(self, allowed: bool) -> bool:
        success = True
        
        paths = [self.CHROME_POLICY_PATH, self.EDGE_POLICY_PATH]
        for hive in [RegistryHive.HKEY_LOCAL_MACHINE, RegistryHive.HKEY_CURRENT_USER]:
            for path in paths:
                self.create_key(hive, path)
                self.write_value(hive, path, "FileSelectionDialogsEnabled", 1 if allowed else 0, RegistryValueType.REG_DWORD)
        
        shell_paths = [
            r"Software\Microsoft\Windows\CurrentVersion\Policies\Comdlg32",
            r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
            r"Software\Policies\Microsoft\Windows\Sidebar"
        ]
        for hive in [RegistryHive.HKEY_LOCAL_MACHINE, RegistryHive.HKEY_CURRENT_USER]:
            for path in shell_paths:
                self.create_key(hive, path)
                self.write_value(hive, path, "NoFileOpen", 0 if allowed else 1, RegistryValueType.REG_DWORD)
                self.write_value(hive, path, "NoFileSaveAs", 0 if allowed else 1, RegistryValueType.REG_DWORD)
                self.write_value(hive, path, "NoDragDrop", 0 if allowed else 1, RegistryValueType.REG_DWORD)
        
        try:
            import ctypes
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
        except Exception:
            pass
            
        return success


    def apply_url_blocklist(self, domains: List[str]) -> bool:
        if sys.platform != 'win32': return False
        
        hives = [RegistryHive.HKEY_LOCAL_MACHINE, RegistryHive.HKEY_CURRENT_USER]
        paths = [
            (self.CHROME_POLICY_PATH, "URLBlocklist"),
            (self.EDGE_POLICY_PATH, "URLBlocklist")
        ]
        
        success = True
        for hive in hives:
            for base_path, value_name in paths:
                full_path = f"{base_path}\\{value_name}"
                self.create_key(hive, full_path)
                
                for i, domain in enumerate(domains, 1):
                    if not self.write_value(hive, full_path, str(i), domain):
                        success = False
        return success

    def block_removable_storage(self) -> bool:
        """
        Block all removable storage via Group Policy registry keys.
        
        This is more comprehensive than just disabling USBSTOR.
        """
        # GUID for removable disks
        removable_disk_guid = "{53f5630d-b6bf-11d0-94f2-00a0c91efb8b}"
        path = f"{self.REMOVABLE_STORAGE_PATH}\\{removable_disk_guid}"
        
        # Create key if needed
        self.create_key(RegistryHive.HKEY_LOCAL_MACHINE, path)
        
        # Set deny flags
        success = True
        for policy in ["Deny_Read", "Deny_Write", "Deny_Execute"]:
            if not self.write_value(
                RegistryHive.HKEY_LOCAL_MACHINE,
                path,
                policy,
                1,
                RegistryValueType.REG_DWORD
            ):
                success = False
        
        return success
    
    def unblock_removable_storage(self) -> bool:
        """Remove removable storage blocking policies."""
        removable_disk_guid = "{53f5630d-b6bf-11d0-94f2-00a0c91efb8b}"
        path = f"{self.REMOVABLE_STORAGE_PATH}\\{removable_disk_guid}"
        
        if not self.key_exists(RegistryHive.HKEY_LOCAL_MACHINE, path):
            return True
        
        # Remove deny flags
        for policy in ["Deny_Read", "Deny_Write", "Deny_Execute"]:
            self.delete_value(RegistryHive.HKEY_LOCAL_MACHINE, path, policy)
        
        return True


# Factory function for cross-platform compatibility
def get_registry_manager() -> Optional[RegistryManager]:
    """Get registry manager (Windows only)."""
    if sys.platform != 'win32':
        return None
    try:
        return RegistryManager()
    except Exception:
        return None
