"""
Endpoint Security Agent - Main Entry Point

This is the main agent that orchestrates all security modules:
- File scanning and S3 backup
- USB device control
- Network monitoring and website blocking
- Sensitive data detection
"""

import sys
import signal
import argparse
import threading
import time
import httpx
import json
import socket
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.core.config import Config, get_config
from agent.core.logger import Logger, setup_logger, EventType
from agent.modules.file_scanner import FileScanner
from agent.modules.usb_control import USBController, USBMode, USBDevice
from agent.modules.network_guard import NetworkGuard, BlockingMethod
from agent.modules.dlp_guard import DataLossGuard
from agent.modules.data_detector import DataDetector, Detection
from agent.utils.s3_client import S3Client


class EndpointSecurityAgent:
    """
    Main Endpoint Security Agent.
    
    Orchestrates all security modules and handles lifecycle.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the agent."""
        # Load configuration
        self.config = get_config(config_path)
        
        # Setup logging
        self.logger = setup_logger(self.config)
        
        # Module instances
        self.file_scanner: Optional[FileScanner] = None
        self.usb_controller: Optional[USBController] = None
        self.network_guard: Optional[NetworkGuard] = None
        self.dlp_guard: Optional[DataLossGuard] = None
        self.data_detector: Optional[DataDetector] = None
        self.s3_client: Optional[S3Client] = None
        
        # State
        self._running = False
        self._heartbeat_thread: Optional[threading.Thread] = None
    
    def _init_s3_client(self) -> Optional[S3Client]:
        """Initialize S3 client if backup is enabled."""
        if not self.config.backup.enabled:
            return None
        
        s3_cfg = self.config.backup.s3
        bucket = s3_cfg.bucket if hasattr(s3_cfg, 'bucket') else s3_cfg.get('bucket', '')
        
        if not bucket:
            self.logger.warning("S3 bucket not configured, backup disabled")
            return None
        
        try:
            region = s3_cfg.region if hasattr(s3_cfg, 'region') else s3_cfg.get('region', 'us-east-1')
            access_key = s3_cfg.access_key_id if hasattr(s3_cfg, 'access_key_id') else s3_cfg.get('access_key_id')
            secret_key = s3_cfg.secret_access_key if hasattr(s3_cfg, 'secret_access_key') else s3_cfg.get('secret_access_key')
            storage_class = s3_cfg.storage_class if hasattr(s3_cfg, 'storage_class') else s3_cfg.get('storage_class', 'STANDARD_IA')
            
            return S3Client(
                bucket=bucket,
                region=region,
                access_key_id=access_key,
                secret_access_key=secret_key,
                storage_class=storage_class,
                max_mbps=self.config.backup.throttle_max_mbps if self.config.backup.throttle_enabled else None
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {e}")
            return None
    
    def _init_file_scanner(self) -> Optional[FileScanner]:
        """Initialize file scanner module."""
        if not self.config.backup.enabled or not self.s3_client:
            return None
        
        try:
            return FileScanner(
                scan_paths=self.config.backup.scan_paths,
                exclude_paths=self.config.backup.exclude_paths,
                exclude_patterns=self.config.backup.exclude_patterns,
                s3_client=self.s3_client,
                hash_db_path=self.config.backup.hash_db_path,
                s3_prefix=self.config.get_s3_prefix(),
                max_file_size_mb=self.config.backup.max_file_size_mb,
                min_file_size_bytes=self.config.backup.min_file_size_bytes,
                hash_algorithm=self.config.backup.hash_algorithm,
                on_file_backed_up=self._on_file_backed_up,
                on_file_changed=self._on_file_changed,
                on_error=self._on_file_error
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize file scanner: {e}")
            return None
    
    def _init_usb_controller(self) -> Optional[USBController]:
        """Initialize USB controller module."""
        if not self.config.usb.enabled:
            return None
        
        try:
            mode = USBMode(self.config.usb.mode)
            
            return USBController(
                mode=mode,
                block_mass_storage=self.config.usb.block_mass_storage,
                block_mtp=self.config.usb.block_mtp,
                block_ptp=self.config.usb.block_ptp,
                whitelist=self.config.usb.whitelist,
                on_device_connected=self._on_usb_connected,
                on_device_blocked=self._on_usb_blocked,
                on_file_operation=None  # TODO: Implement file operation monitoring
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize USB controller: {e}")
            return None
    
    def _init_network_guard(self) -> Optional[NetworkGuard]:
        """Initialize network guard module."""
        if not self.config.network.enabled:
            return None
        
        try:
            method = BlockingMethod(self.config.network.blocking_method)
            
            return NetworkGuard(
                blocking_method=method,
                blocked_sites=self.config.network.blocked_sites,
                blocked_categories=self.config.network.blocked_categories,
                allowed_sites=self.config.network.allowed_sites,
                log_connections=self.config.network.log_connections,
                log_dns=self.config.network.log_dns,
                track_bandwidth=self.config.network.track_bandwidth,
                on_blocked=self._on_network_blocked,
                on_connection=self._on_network_connection,
                on_dns_query=self._on_dns_query
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize network guard: {e}")
            return None

    def _init_dlp_guard(self) -> Optional[DataLossGuard]:
        """Initialize DLP (Upload Blocking) guard module."""
        try:
            return DataLossGuard(
                logger=self.logger,
                block_all=False, # Default to off until config received
                whitelist=[]
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize DLP guard: {e}")
            return None
    
    def _init_data_detector(self) -> Optional[DataDetector]:
        """Initialize data detector module."""
        if not self.config.data_detection.enabled:
            return None
        
        try:
            return DataDetector(
                detect_credit_cards=self.config.data_detection.detect_credit_cards,
                detect_ssn=self.config.data_detection.detect_ssn,
                detect_email=self.config.data_detection.detect_email,
                detect_phone=self.config.data_detection.detect_phone,
                detect_ip=self.config.data_detection.detect_ip,
                custom_patterns=self.config.data_detection.custom_patterns,
                scan_extensions=self.config.data_detection.scan_extensions,
                on_detection=self._on_sensitive_data_found
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize data detector: {e}")
            return None
    
    # Event handlers
    def _on_file_backed_up(self, path: str, size: int, s3_key: str):
        """Handle file backup completion."""
        self.logger.file_backed_up(path, size, s3_key)
    
    def _on_file_changed(self, event_type: str, path: str):
        """Handle file change event."""
        self.logger.debug(f"File {event_type}: {path}")
    
    def _on_file_error(self, path: str, error: str):
        """Handle file operation error."""
        self.logger.file_backup_failed(path, error)
    
    def _on_usb_connected(self, device: USBDevice):
        """Handle USB device connection."""
        self.logger.usb_connected({
            'device_id': device.device_id,
            'vendor_id': device.vendor_id,
            'product_id': device.product_id,
            'description': device.description,
            'drive_letter': device.drive_letter
        })
    
    def _on_usb_blocked(self, device: USBDevice, reason: str):
        """Handle USB device blocking."""
        self.logger.usb_blocked({
            'device_id': device.device_id,
            'vendor_id': device.vendor_id,
            'product_id': device.product_id,
            'description': device.description
        }, reason)
    
    def _on_network_blocked(self, domain: str, reason: str):
        """Handle network blocking."""
        self.logger.network_blocked(domain, reason)
    
    def _on_network_connection(self, conn):
        """Handle network connection."""
        self.logger.debug(
            f"Connection: {conn.process_name} -> {conn.remote_address}:{conn.remote_port}"
        )
    
    def _on_dns_query(self, query):
        """Handle DNS query."""
        if query.blocked:
            self.logger.debug(f"DNS blocked: {query.domain}")
    
    def _on_sensitive_data_found(self, source: str, detection: Detection):
        """Handle sensitive data detection."""
        self.logger.sensitive_data_found(
            source,
            detection.data_type.value,
            1
        )
    
    def _heartbeat_loop(self):
        self.logger.info("Heartbeat loop started")
        
        while self._running:
            # Only attempt heartbeat if we have an API key
            if not self.config.agent.api_key:
                time.sleep(5)
                # Try to register again if key is missing
                self._register_agent()
                continue

            try:
                stats = {}
                if self.file_scanner:
                    fs_stats = self.file_scanner.get_statistics()
                    stats['files_backed_up'] = fs_stats.get('total_files', 0)
                    stats['backup_size'] = fs_stats.get('total_size_bytes', 0)
                
                # Send heartbeat
                url = f"{self.config.agent.dashboard_url}/api/v1/agent/heartbeat"
                headers = {"X-API-Key": self.config.agent.api_key}
                payload = {
                    "status": "online",
                    "stats": stats
                }
                
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(url, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        new_config_data = response.json().get('config', {})
                        if new_config_data:
                            self._apply_new_config(new_config_data)
                    else:
                        self.logger.error(f"Heartbeat failed: {response.status_code} - {response.text}")
                        
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
            
            # Sleep for configured interval
            for _ in range(self.config.agent.heartbeat_interval):
                if not self._running:
                    break
                time.sleep(1)

    def _apply_new_config(self, config_data: dict):
        """Apply new configuration received from dashboard."""
        try:
            self.logger.info(f"Applying new configuration: {list(config_data.keys())}")
            
            # Update network blocking
            if 'network' in config_data and self.network_guard:
                network_cfg = config_data['network']
                blocked_sites = network_cfg.get('blocked_sites', [])
                self.logger.info(f"Syncing {len(blocked_sites)} blocked sites")
                
                # Update blocked sites in guard
                current_blocked = set(self.network_guard.get_blocked_domains())
                new_blocked = set(s.lower() for s in blocked_sites)
                
                # Add new ones
                for site in new_blocked - current_blocked:
                    self.network_guard.add_blocked_site(site)
                    self.logger.info(f"Added blocked site: {site}")
                    
                # Remove deleted ones
                for site in current_blocked - new_blocked:
                    self.network_guard.remove_blocked_site(site)
                    self.logger.info(f"Removed blocked site: {site}")

            # Update USB whitelist
            if 'usb' in config_data and self.usb_controller:
                usb_cfg = config_data['usb']
                whitelist = usb_cfg.get('whitelist', [])
                self.usb_controller.whitelist = whitelist
                
                if 'mode' in usb_cfg:
                    self.usb_controller.set_mode(USBMode(usb_cfg['mode']))

            # Update DLP (Upload) blocking
            # We look for both 'uploads' and 'uploads_rules' to be safe
            dlp_cfg = config_data.get('uploads') or config_data.get('uploads_rules')
            
            if dlp_cfg and self.dlp_guard:
                block_all = dlp_cfg.get('block_all', False)
                whitelist = dlp_cfg.get('whitelist', [])
                
                self.logger.info(f"DLP Sync: block_all={block_all}, whitelist={len(whitelist)}")
                
                # Always call set_config which now handles its own change detection and browser killing
                self.dlp_guard.set_config(block_all, whitelist)
                
                # Ensure it's running if block_all is True
                if block_all and not self.dlp_guard._running:
                    self.dlp_guard.start()
                elif not block_all and self.dlp_guard._running:
                    self.dlp_guard.stop()
                    
        except Exception as e:
            self.logger.error(f"Error applying new config: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def _register_agent(self) -> bool:
        """Register agent with dashboard if API key is missing."""
        if self.config.agent.api_key:
            return True
            
        self.logger.info("Registering agent with dashboard...")
        url = f"{self.config.agent.dashboard_url}/api/v1/endpoints/register"
        payload = {
            "machine_id": self.config.agent.machine_id,
            "hostname": self.config.agent.hostname,
            "agent_version": self.config.agent.version,
            "os_version": sys.platform,
            "ip_address": socket.gethostbyname(socket.gethostname())
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload)
                if response.status_code in (200, 201):
                    data = response.json()
                    self.config.agent.api_key = data['api_key']
                    # Save api_key to config file
                    self.config.save()
                    self.logger.info("Agent registered successfully")
                    return True
                else:
                    self.logger.error(f"Registration failed: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return False

    def _start_guardian(self):
        """Spawn the guardian process to ensure self-protection."""
        if sys.platform != 'win32':
            return
            
        try:
            # Check if guardian is already running
            import psutil
            for proc in psutil.process_iter(['name', 'cmdline']):
                if proc.info['name'] == 'python.exe' and 'guardian.py' in str(proc.info['cmdline']):
                    return

            # Start guardian
            guardian_path = Path(__file__).parent / "core" / "guardian.py"
            subprocess.Popen(
                [sys.executable, str(guardian_path)],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            )
            self.logger.info("Self-protection guardian started")
        except Exception as e:
            self.logger.error(f"Failed to start guardian: {e}")


    def start(self):
        """Start the agent and all modules."""
        if self._running:
            return
            
        # Start self-protection
        self._start_guardian()
        
        # Register first
        if not self._register_agent():
            self.logger.error("Could not register agent, starting in offline mode")
        
        self._running = True
        self.logger.agent_started()
        
        # Initialize modules
        self.s3_client = self._init_s3_client()
        self.file_scanner = self._init_file_scanner()
        self.usb_controller = self._init_usb_controller()
        self.network_guard = self._init_network_guard()
        self.dlp_guard = self._init_dlp_guard()
        self.data_detector = self._init_data_detector()
        
        # Start modules
        if self.file_scanner:
            self.file_scanner.start_monitoring()
            self.logger.info("File scanner started")
        
        if self.usb_controller:
            self.usb_controller.start()
            self.logger.info(f"USB controller started in {self.config.usb.mode} mode")
        
        if self.network_guard:
            self.network_guard.start()
            self.logger.info("Network guard started")
            
        if self.dlp_guard:
            self.dlp_guard.start()
            self.logger.info("DLP guard started")
        
        # Start heartbeat thread
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        
        self.logger.info("Endpoint Security Agent fully started")
    
    def stop(self):
        """Stop the agent and all modules."""
        if not self._running:
            return
        
        self._running = False
        
        # Stop modules
        if self.file_scanner:
            self.file_scanner.stop_monitoring()
            self.logger.info("File scanner stopped")
        
        if self.usb_controller:
            self.usb_controller.stop()
            self.logger.info("USB controller stopped")
        
        if self.network_guard:
            self.network_guard.stop()
            self.logger.info("Network guard stopped")
            
        if self.dlp_guard:
            self.dlp_guard.stop()
            self.logger.info("DLP guard stopped")
        
        # Wait for heartbeat thread
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        
        self.logger.agent_stopped("normal")
    
    def run_initial_scan(self):
        """Run initial file scan."""
        if not self.file_scanner:
            self.logger.warning("File scanner not initialized, skipping initial scan")
            return
        
        self.logger.info("Starting initial file scan...")
        
        def progress(path, scanned, total):
            if scanned % 1000 == 0:
                self.logger.info(f"Scan progress: {scanned}/{total} files")
        
        self.file_scanner.scan_all(callback=progress)
        
        stats = self.file_scanner.get_statistics()
        self.logger.info(f"Initial scan complete: {stats['total_files']} files, {stats['queue_size']} pending backup")
    
    def get_status(self) -> dict:
        """Get agent status summary."""
        status = {
            'running': self._running,
            'machine_id': self.config.agent.machine_id,
            'hostname': self.config.agent.hostname,
            'modules': {
                'file_scanner': self.file_scanner is not None,
                'usb_controller': self.usb_controller is not None,
                'network_guard': self.network_guard is not None,
                'data_detector': self.data_detector is not None
            }
        }
        
        if self.file_scanner:
            status['backup_stats'] = self.file_scanner.get_statistics()
        
        if self.usb_controller:
            status['usb_devices'] = len(self.usb_controller.get_connected_devices())
        
        if self.network_guard:
            status['blocked_sites'] = len(self.network_guard.get_blocked_domains())
        
        return status


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Endpoint Security Agent")
    parser.add_argument("--config", type=Path, help="Path to configuration file")
    parser.add_argument("--foreground", action="store_true", help="Run in foreground (not as service)")
    parser.add_argument("--scan", action="store_true", help="Run initial file scan")
    
    # Service commands
    subparsers = parser.add_subparsers(dest="command", help="Service commands")
    subparsers.add_parser("install", help="Install as Windows service")
    subparsers.add_parser("uninstall", help="Uninstall Windows service")
    subparsers.add_parser("start", help="Start Windows service")
    subparsers.add_parser("stop", help="Stop Windows service")
    subparsers.add_parser("status", help="Get service status")
    
    args = parser.parse_args()
    
    # Handle service commands
    if args.command:
        from agent.core.service import (
            install_service, uninstall_service, start_service, 
            stop_service, get_service_status, EndpointSecurityService
        )
        import win32serviceutil
        
        if args.command in ["install", "remove", "uninstall", "start", "stop", "restart"]:
            # Use the standard pywin32 handler for these commands
            # This ensures the service is registered with the correct Python path
            cmd = "remove" if args.command == "uninstall" else args.command
            sys.argv = [sys.argv[0], cmd]
            win32serviceutil.HandleCommandLine(EndpointSecurityService)
            
            # Post-install configuration
            if args.command == "install":
                from agent.core.service import set_service_recovery, configure_service_path
                configure_service_path()
                set_service_recovery()
            return
            
        if args.command == "status":
            print(f"Service status: {get_service_status()}")
        return

    # Default to foreground if no command and --foreground is set
    if args.foreground:
        agent = EndpointSecurityAgent(args.config)
        
        # Handle termination signals
        def signal_handler(sig, frame):
            print("\n[*] Stopping agent...")
            agent.stop()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        agent.start()
        
        if args.scan:
            agent.run_initial_scan()
            
        print("\nEndpoint Security Agent running")
        print(f"Machine ID: {agent.config.agent.machine_id}")
        print("Press Ctrl+C to stop\n")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
    else:
        # If no arguments provided on Windows, try to run as service
        if sys.platform == 'win32' and not args.foreground:
            from agent.core.service import EndpointSecurityService
            import win32serviceutil
            win32serviceutil.HandleCommandLine(EndpointSecurityService)
        else:
            parser.print_help()

if __name__ == "__main__":
    main()
