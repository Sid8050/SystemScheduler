"""
USB Device Control Module for Endpoint Security Agent

Provides:
- USB storage device blocking/monitoring
- Device whitelisting by VID/PID
- File operation logging on USB devices
- Real-time device connection monitoring
"""

import sys
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Windows-specific imports
if sys.platform == 'win32':
    import wmi
    import win32file
    import win32api
    import pythoncom
    import psutil
else:
    wmi = None
    win32file = None
    win32api = None
    pythoncom = None
    psutil = None

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.registry import RegistryManager, RegistryHive, RegistryValueType


class USBMode(str, Enum):
    """USB control modes."""
    MONITOR = "monitor"      # Log only, don't block
    BLOCK = "block"          # Block all USB storage
    WHITELIST = "whitelist"  # Only allow whitelisted devices


@dataclass
class USBDevice:
    """Information about a USB device."""
    device_id: str
    vendor_id: str
    product_id: str
    serial_number: Optional[str]
    description: str
    drive_letter: Optional[str]
    device_type: str  # mass_storage, mtp, ptp, hid, etc.
    connected_time: datetime
    
    def matches_whitelist(self, whitelist: List[Dict]) -> bool:
        """Check if device matches any whitelist entry."""
        for entry in whitelist:
            vid = entry.get('vid', '*')
            pid = entry.get('pid', '*')
            serial = entry.get('serial')
            
            # Check VID
            if vid != '*' and vid.lower() != self.vendor_id.lower():
                continue
            
            # Check PID
            if pid != '*' and pid.lower() != self.product_id.lower():
                continue
            
            # Check serial if specified
            if serial and serial != self.serial_number:
                continue
            
            return True
        
        return False


@dataclass
class USBFileEvent:
    """File operation event on USB device."""
    timestamp: datetime
    operation: str  # copy_to, copy_from, delete, rename
    source_path: str
    dest_path: Optional[str]
    file_size: int
    device_id: str
    drive_letter: str


class USBController:
    """
    USB device control and monitoring.
    
    Provides device blocking, whitelisting, and file operation monitoring.
    """
    
    def __init__(
        self,
        mode: USBMode = USBMode.MONITOR,
        block_mass_storage: bool = True,
        block_mtp: bool = True,
        block_ptp: bool = False,
        whitelist: Optional[List[Dict]] = None,
        on_device_connected: Optional[Callable[[USBDevice], None]] = None,
        on_device_blocked: Optional[Callable[[USBDevice, str], None]] = None,
        on_file_operation: Optional[Callable[[USBFileEvent], None]] = None
    ):
        self.mode = mode
        self.block_mass_storage = block_mass_storage
        self.block_mtp = block_mtp
        self.block_ptp = block_ptp
        self.whitelist = whitelist or []
        
        # Callbacks
        self.on_device_connected = on_device_connected
        self.on_device_blocked = on_device_blocked
        self.on_file_operation = on_file_operation
        
        # State
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._connected_devices: Dict[str, USBDevice] = {}
        self._registry: Optional[RegistryManager] = None
        
        # Initialize registry manager
        if sys.platform == 'win32':
            self._registry = RegistryManager()
    
    def _get_removable_drives(self) -> Dict[str, str]:
        """Get mapping of drive letters to device IDs for removable drives."""
        drives = {}
        
        if psutil is None:
            return drives
        
        for partition in psutil.disk_partitions():
            if 'removable' in partition.opts.lower():
                try:
                    drive = partition.mountpoint.rstrip('\\')
                    # Get volume info
                    if win32api:
                        volume_info = win32api.GetVolumeInformation(f"{drive}\\")
                        drives[drive] = {
                            'label': volume_info[0],
                            'serial': volume_info[1],
                            'fstype': partition.fstype
                        }
                except Exception:
                    drives[drive] = {'label': '', 'serial': '', 'fstype': ''}
        
        return drives
    
    def _parse_device_id(self, device_id: str) -> Dict:
        """Parse USB device ID to extract VID/PID."""
        # Format: USB\VID_XXXX&PID_XXXX\SERIAL
        parts = device_id.upper().split('\\')
        
        vid = ""
        pid = ""
        serial = ""
        
        for part in parts:
            if 'VID_' in part:
                # Extract VID and PID
                for segment in part.split('&'):
                    if segment.startswith('VID_'):
                        vid = segment[4:8]
                    elif segment.startswith('PID_'):
                        pid = segment[4:8]
            elif part and 'VID' not in part and 'PID' not in part:
                serial = part
        
        return {'vid': vid, 'pid': pid, 'serial': serial}
    
    def _detect_device_type(self, device_id: str, compatible_ids: List[str]) -> str:
        """Detect USB device type from compatible IDs."""
        device_id_lower = device_id.lower()
        
        if 'usbstor' in device_id_lower:
            return 'mass_storage'
        
        for compat in compatible_ids:
            compat_lower = compat.lower()
            if 'class_08' in compat_lower:  # Mass storage
                return 'mass_storage'
            elif 'class_06' in compat_lower:  # PTP
                return 'ptp'
            elif 'class_03' in compat_lower:  # HID
                return 'hid'
            elif 'mtp' in compat_lower or 'wpdbusenum' in compat_lower:
                return 'mtp'
        
        return 'unknown'
    
    def _get_connected_usb_devices(self) -> List[USBDevice]:
        devices = []
        
        if wmi is None:
            return devices
        
        try:
            pythoncom.CoInitialize()
            c = wmi.WMI()
            
            for pnp in c.Win32_PnPEntity():
                pnp_id = pnp.PNPDeviceID or ''
                
                if 'VID_' not in pnp_id.upper() or 'PID_' not in pnp_id.upper():
                    continue
                
                if any(d.device_id == pnp_id for d in devices):
                    continue

                service = (pnp.Service or '').lower()
                compatible_ids = pnp.CompatibleID or []
                desc = (pnp.Description or pnp.Caption or '').lower()
                
                device_type = 'unknown'
                if service == 'usbstor' or 'USBSTOR' in pnp_id.upper():
                    device_type = 'mass_storage'
                elif service == 'hidusb' or 'keyboard' in desc or 'mouse' in desc:
                    device_type = 'hid'
                elif 'usbhub' in service:
                    device_type = 'hub'
                elif 'mtp' in str(compatible_ids).lower() or 'mtp' in service:
                    device_type = 'mtp'
                elif 'ptp' in str(compatible_ids).lower() or 'ptp' in service:
                    device_type = 'ptp'
                
                parsed = self._parse_device_id(pnp_id)
                
                devices.append(USBDevice(
                    device_id=pnp_id,
                    vendor_id=parsed['vid'],
                    product_id=parsed['pid'],
                    serial_number=parsed['serial'] or None,
                    description=pnp.Caption or pnp.Description or 'USB Device',
                    drive_letter=None,
                    device_type=device_type,
                    connected_time=datetime.now()
                ))

            for disk in c.Win32_DiskDrive(InterfaceType='USB'):
                disk_pnp = disk.PNPDeviceID
                
                drive_letter = None
                for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                    for logical in partition.associators("Win32_LogicalDiskToPartition"):
                        drive_letter = logical.DeviceID
                        break
                
                disk_parsed = self._parse_device_id(disk_pnp)
                
                found = False
                for d in devices:
                    if d.device_id == disk_pnp:
                        d.drive_letter = drive_letter
                        d.device_type = 'mass_storage'
                        found = True
                        break
                    if d.serial_number and disk_parsed['serial'] and d.serial_number == disk_parsed['serial']:
                        d.drive_letter = drive_letter
                        d.device_type = 'mass_storage'
                        found = True
                        break
                
                if not found:
                    devices.append(USBDevice(
                        device_id=disk_pnp,
                        vendor_id=disk_parsed['vid'],
                        product_id=disk_parsed['pid'],
                        serial_number=disk_parsed['serial'] or None,
                        description=disk.Caption or disk.Model or 'USB Storage Device',
                        drive_letter=drive_letter,
                        device_type='mass_storage',
                        connected_time=datetime.now()
                    ))
            
        except Exception as e:
            print(f"Error in USB scan: {e}")
        finally:
            try:
                pythoncom.CoUninitialize()
            except:
                pass
        
        return devices
    
    # Device types that should NEVER be blocked (critical system devices)
    PROTECTED_DEVICE_TYPES = {'hid', 'hub', 'bluetooth', 'network', 'audio', 'video', 'printer'}

    def _is_protected_device(self, device: USBDevice) -> bool:
        """
        Check if device is a protected type that should NEVER be blocked.
        This includes mice, keyboards, network adapters, Bluetooth, etc.
        """
        # Protected by device type
        if device.device_type in self.PROTECTED_DEVICE_TYPES:
            return True

        # Additional protection by description keywords
        desc_lower = device.description.lower()
        protected_keywords = [
            'keyboard', 'mouse', 'hid', 'input device',
            'bluetooth', 'wireless', 'lan', 'ethernet', 'network',
            'audio', 'sound', 'speaker', 'microphone',
            'webcam', 'camera', 'video',
            'hub', 'root hub',
            'printer', 'scanner'
        ]

        for keyword in protected_keywords:
            if keyword in desc_lower:
                return True

        return False

    def _should_block_device(self, device: USBDevice) -> tuple:
        """
        Determine if a device should be blocked.

        Returns: (should_block, reason)
        """
        # NEVER block protected devices (mice, keyboards, network, etc.)
        if self._is_protected_device(device):
            return False, None

        if self.mode == USBMode.MONITOR:
            return False, None

        # Check whitelist first
        if self.mode == USBMode.WHITELIST:
            if device.matches_whitelist(self.whitelist):
                return False, None
            # Even in whitelist mode, don't block non-storage devices
            if device.device_type not in ('mass_storage', 'mtp', 'ptp'):
                return False, None
            return True, "Device not in whitelist"

        # Block mode - ONLY block storage-type devices
        if self.mode == USBMode.BLOCK:
            if device.device_type == 'mass_storage' and self.block_mass_storage:
                return True, "Mass storage devices are blocked"
            if device.device_type == 'mtp' and self.block_mtp:
                return True, "MTP devices are blocked"
            if device.device_type == 'ptp' and self.block_ptp:
                return True, "PTP devices are blocked"

        return False, None
    
    def _block_device(self, device: USBDevice, reason: str):
        """Block a USB device."""
        # Method 1: Disable USBSTOR service (blocks all USB storage)
        if device.device_type == 'mass_storage' and self._registry:
            self._registry.set_usb_storage_state(False)
        
        # Method 2: Eject the specific drive
        if device.drive_letter and win32file:
            try:
                drive = f"\\\\.\\{device.drive_letter}"
                handle = win32file.CreateFile(
                    drive,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )
                # Eject
                win32file.DeviceIoControl(handle, 0x2D4808, None, None)  # IOCTL_STORAGE_EJECT_MEDIA
                win32file.CloseHandle(handle)
            except Exception as e:
                print(f"Error ejecting device: {e}")
        
        # Callback
        if self.on_device_blocked:
            self.on_device_blocked(device, reason)
    
    def _monitor_loop(self):
        """Main monitoring loop for USB device changes."""
        if wmi is None:
            return

        pythoncom.CoInitialize()

        try:
            c = wmi.WMI()

            # Monitor device insertions
            watcher = c.Win32_DeviceChangeEvent.watch_for(
                notification_type="Creation"
            )

            while self._running:
                try:
                    # Check for new device (with shorter timeout for faster response)
                    event = watcher(timeout_ms=500)

                    if event:
                        # Shorter delay - just enough for device to register
                        time.sleep(0.5)

                        # Get current devices
                        current_devices = self._get_connected_usb_devices()

                        for device in current_devices:
                            if device.device_id not in self._connected_devices:
                                # New device detected
                                self._connected_devices[device.device_id] = device
                                print(f"[USB] New device: {device.description} ({device.device_type})")

                                # Check if should block
                                should_block, reason = self._should_block_device(device)

                                if should_block:
                                    print(f"[USB] BLOCKING: {device.description} - {reason}")
                                    self._block_device(device, reason)
                                else:
                                    # Callback for new device
                                    if self.on_device_connected:
                                        self.on_device_connected(device)

                        # Check for removed devices
                        current_ids = {d.device_id for d in current_devices}
                        removed = [did for did in self._connected_devices if did not in current_ids]

                        for device_id in removed:
                            del self._connected_devices[device_id]

                except wmi.x_wmi_timed_out:
                    # In block mode, periodically scan for any devices that slipped through
                    if self.mode == USBMode.BLOCK:
                        self._check_and_block_new_storage()
                    continue
                except Exception as e:
                    print(f"USB monitor error: {e}")
                    time.sleep(1)
        
        finally:
            pythoncom.CoUninitialize()
    
    def start(self):
        """Start USB monitoring."""
        if self._running:
            return

        self._running = True

        # Initial device scan
        for device in self._get_connected_usb_devices():
            self._connected_devices[device.device_id] = device

        # Apply initial blocking policy if in block mode
        if self.mode == USBMode.BLOCK and self.block_mass_storage:
            if self._registry:
                self._registry.set_usb_storage_state(False)
                self._registry.block_removable_storage()
            # Eject non-whitelisted mass storage devices
            self._eject_all_mass_storage()

        # Start monitor thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop(self):
        """Stop USB monitoring."""
        self._running = False

        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

        # Re-enable USB storage if we disabled it
        if self.mode == USBMode.BLOCK and self._registry:
            self._registry.set_usb_storage_state(True)
            self._registry.unblock_removable_storage()
    
    def get_connected_devices(self) -> List[USBDevice]:
        """Get list of currently connected USB devices."""
        # If no devices cached, do a fresh scan
        if not self._connected_devices:
            self.rescan_devices()
        return list(self._connected_devices.values())
    
    def is_device_allowed(self, device: USBDevice) -> bool:
        """Check if a device is allowed based on current policy."""
        should_block, _ = self._should_block_device(device)
        return not should_block
    
    def add_to_whitelist(self, vid: str, pid: str, serial: Optional[str] = None, description: str = ""):
        """Add a device to the whitelist."""
        entry = {
            'vid': vid,
            'pid': pid,
            'description': description
        }
        if serial:
            entry['serial'] = serial
        
        self.whitelist.append(entry)
    
    def remove_from_whitelist(self, vid: str, pid: str):
        """Remove a device from the whitelist."""
        self.whitelist = [
            e for e in self.whitelist
            if not (e.get('vid') == vid and e.get('pid') == pid)
        ]
    
    def set_mode(self, mode: USBMode):
        """Change the USB control mode."""
        old_mode = self.mode
        self.mode = mode

        print(f"[USB] Mode changing: {old_mode.value if old_mode else 'None'} -> {mode.value}")

        # Apply new policy
        if mode == USBMode.BLOCK and self.block_mass_storage:
            if self._registry:
                print("[USB] Applying blocking policies...")
                # Disable USBSTOR driver
                result1 = self._registry.set_usb_storage_state(False)
                print(f"[USB] USBSTOR disabled: {result1}")

                # Apply Group Policy blocking
                result2 = self._registry.block_removable_storage()
                print(f"[USB] Removable storage policy applied: {result2}")

                # Force Group Policy refresh for immediate effect
                self._refresh_group_policy()

            # Eject currently connected mass storage devices
            self._eject_all_mass_storage()

        elif old_mode == USBMode.BLOCK and mode != USBMode.BLOCK:
            # Re-enable USB
            print("[USB] Re-enabling USB storage...")
            if self._registry:
                self._registry.set_usb_storage_state(True)
                self._registry.unblock_removable_storage()
                self._refresh_group_policy()

    def _refresh_group_policy(self):
        """Force Windows to refresh Group Policy for immediate effect."""
        try:
            import subprocess
            # Run gpupdate to refresh policies
            subprocess.run(
                ['gpupdate', '/force'],
                capture_output=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            print("[USB] Group Policy refreshed")
        except Exception as e:
            print(f"[USB] Failed to refresh Group Policy: {e}")

    def _eject_all_mass_storage(self):
        """Eject all currently connected mass storage devices (NOT mice/keyboards/network)."""
        if win32file is None:
            return

        for device in list(self._connected_devices.values()):
            # SAFETY: Skip protected devices (mice, keyboards, network, etc.)
            if self._is_protected_device(device):
                continue

            # Only eject mass storage devices with drive letters
            if device.device_type == 'mass_storage' and device.drive_letter:
                # Check if whitelisted
                if device.matches_whitelist(self.whitelist):
                    print(f"Skipping whitelisted device: {device.description}")
                    continue

                print(f"Ejecting USB storage: {device.description} ({device.drive_letter})")
                try:
                    drive = f"\\\\.\\{device.drive_letter}"
                    handle = win32file.CreateFile(
                        drive,
                        win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None
                    )
                    # Lock and dismount volume first
                    try:
                        win32file.DeviceIoControl(handle, 0x00090018, None, None)  # FSCTL_LOCK_VOLUME
                        win32file.DeviceIoControl(handle, 0x00090020, None, None)  # FSCTL_DISMOUNT_VOLUME
                    except Exception:
                        pass
                    # Eject media
                    win32file.DeviceIoControl(handle, 0x2D4808, None, None)  # IOCTL_STORAGE_EJECT_MEDIA
                    win32file.CloseHandle(handle)

                    if self.on_device_blocked:
                        self.on_device_blocked(device, "USB blocking enabled - device ejected")
                except Exception as e:
                    print(f"Error ejecting device {device.drive_letter}: {e}")

    def _check_and_block_new_storage(self):
        """Periodically check for any mass storage that slipped through and block it."""
        if self.mode != USBMode.BLOCK:
            return

        try:
            current_devices = self._get_connected_usb_devices()
            for device in current_devices:
                if device.device_id not in self._connected_devices:
                    self._connected_devices[device.device_id] = device

                # Check if it's a mass storage device that should be blocked
                if device.device_type == 'mass_storage' and device.drive_letter:
                    if not self._is_protected_device(device) and not device.matches_whitelist(self.whitelist):
                        print(f"[USB] Catching missed storage device: {device.description}")
                        self._block_device(device, "Mass storage devices are blocked")
        except Exception as e:
            print(f"[USB] Error in periodic check: {e}")

    def rescan_devices(self):
        """Force a rescan of connected USB devices."""
        devices = self._get_connected_usb_devices()
        self._connected_devices.clear()
        for device in devices:
            self._connected_devices[device.device_id] = device
        return devices
    
    def get_device_history(self) -> List[Dict]:
        """Get history of USB devices that have been connected (from registry)."""
        if self._registry is None:
            return []
        
        return self._registry.get_connected_usb_devices()
