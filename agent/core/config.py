"""
Configuration Management for Endpoint Security Agent

Handles loading, validation, and access to configuration settings.
Supports YAML config files with environment variable overrides.
"""

import os
import uuid
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

import yaml


# Default paths
DEFAULT_CONFIG_PATH = Path("C:/ProgramData/EndpointSecurity/config.yaml")
DEFAULT_DATA_DIR = Path("C:/ProgramData/EndpointSecurity")


@dataclass
class S3Config:
    """AWS S3 configuration."""
    bucket: str = ""
    region: str = "us-east-1"
    prefix: str = "backups/{machine_id}/{date}/"
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    storage_class: str = "STANDARD_IA"


@dataclass
class BackupConfig:
    """File backup configuration."""
    enabled: bool = True
    s3: S3Config = field(default_factory=S3Config)
    scan_paths: List[str] = field(default_factory=lambda: ["C:\\Users"])
    exclude_paths: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    max_file_size_mb: int = 500
    min_file_size_bytes: int = 1
    schedule: str = "0 2 * * *"
    incremental_enabled: bool = True
    hash_algorithm: str = "sha256"
    hash_db_path: str = "C:\\ProgramData\\EndpointSecurity\\hashes.db"
    throttle_enabled: bool = False
    throttle_max_mbps: int = 50
    encryption_enabled: bool = True


@dataclass
class USBConfig:
    """USB control configuration."""
    enabled: bool = True
    mode: str = "monitor"  # block | monitor | whitelist
    block_mass_storage: bool = True
    block_mtp: bool = True
    block_ptp: bool = False
    whitelist: List[Dict[str, Any]] = field(default_factory=list)
    log_events: bool = True
    log_file_operations: bool = True
    alert_on_block: bool = True
    alert_on_unknown: bool = True


@dataclass
class NetworkConfig:
    """Network monitoring configuration."""
    enabled: bool = True
    blocking_enabled: bool = True
    blocking_method: str = "hosts"  # hosts | dns_proxy | wfp
    blocked_sites: List[str] = field(default_factory=list)
    blocked_categories: List[str] = field(default_factory=list)
    allowed_sites: List[str] = field(default_factory=list)
    monitoring_enabled: bool = True
    log_connections: bool = True
    log_dns: bool = True
    track_bandwidth: bool = True


@dataclass
class DataDetectionConfig:
    """Sensitive data detection configuration."""
    enabled: bool = True
    detect_credit_cards: bool = True
    detect_ssn: bool = True
    detect_email: bool = True
    detect_phone: bool = True
    detect_ip: bool = False
    custom_patterns: List[Dict[str, Any]] = field(default_factory=list)
    on_detection_log: bool = True
    on_detection_alert: bool = True
    on_detection_block: bool = False
    scan_extensions: List[str] = field(default_factory=lambda: [
        ".txt", ".csv", ".xlsx", ".docx", ".pdf", ".json", ".xml"
    ])


@dataclass 
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    local_enabled: bool = True
    local_path: str = "C:\\ProgramData\\EndpointSecurity\\logs"
    max_size_mb: int = 100
    retention_days: int = 30
    s3_sync_enabled: bool = True
    s3_bucket: Optional[str] = None
    s3_prefix: str = "logs/{machine_id}/"
    s3_sync_interval: int = 3600
    dashboard_sync_enabled: bool = True
    dashboard_batch_size: int = 100
    dashboard_flush_interval: int = 60


@dataclass
class AgentConfig:
    """Main agent configuration."""
    name: str = "EndpointSecurityAgent"
    version: str = "1.0.0"
    machine_id: str = ""
    hostname: str = ""
    heartbeat_interval: int = 60
    dashboard_url: str = "http://localhost:8000"
    api_key: Optional[str] = None


class Config:
    """
    Main configuration class for the Endpoint Security Agent.
    
    Loads configuration from YAML file with support for:
    - Environment variable overrides (ES_* prefix)
    - Default values
    - Runtime modification
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.data_dir = DEFAULT_DATA_DIR
        
        # Initialize with defaults
        self.agent = AgentConfig()
        self.backup = BackupConfig()
        self.usb = USBConfig()
        self.network = NetworkConfig()
        self.data_detection = DataDetectionConfig()
        self.logging = LoggingConfig()
        
        # Set machine-specific defaults
        self._set_machine_defaults()
        
        # Load from file if exists
        if self.config_path.exists():
            self.load()
    
    def _set_machine_defaults(self):
        """Set machine-specific default values."""
        self.agent.hostname = socket.gethostname()
        self.agent.machine_id = self._generate_machine_id()
    
    def _generate_machine_id(self) -> str:
        """Generate a unique machine identifier."""
        # Try to use existing ID from data file
        id_file = self.data_dir / "machine_id"
        if id_file.exists():
            return id_file.read_text().strip()
        
        # Generate new ID based on hostname and hardware
        machine_id = f"{self.agent.hostname}-{uuid.uuid4().hex[:8]}"
        
        # Save for future use
        self.data_dir.mkdir(parents=True, exist_ok=True)
        id_file.write_text(machine_id)
        
        return machine_id
    
    def load(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            return
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        self._load_section(data, 'agent', self.agent)
        self._load_section(data, 'backup', self.backup)
        self._load_section(data, 'usb_control', self.usb)
        self._load_section(data, 'network', self.network)
        self._load_section(data, 'data_detection', self.data_detection)
        self._load_section(data, 'logging', self.logging)
        
        # Load nested S3 config
        if 'backup' in data and 's3' in data['backup']:
            self._load_section(data['backup'], 's3', self.backup.s3)
        
        # Apply environment variable overrides
        self._apply_env_overrides()
    
    def _load_section(self, data: Dict, section: str, config_obj: Any) -> None:
        """Load a configuration section into a dataclass."""
        if section not in data:
            return
        
        section_data = data[section]
        if not isinstance(section_data, dict):
            return
        
        for key, value in section_data.items():
            # Convert YAML keys (snake_case) to attribute names
            attr_name = key.replace('-', '_')
            if hasattr(config_obj, attr_name):
                setattr(config_obj, attr_name, value)
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides (ES_* prefix)."""
        # S3 credentials from environment
        if os.environ.get('AWS_ACCESS_KEY_ID'):
            self.backup.s3.access_key_id = os.environ['AWS_ACCESS_KEY_ID']
        if os.environ.get('AWS_SECRET_ACCESS_KEY'):
            self.backup.s3.secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
        
        # Agent settings
        if os.environ.get('ES_DASHBOARD_URL'):
            self.agent.dashboard_url = os.environ['ES_DASHBOARD_URL']
        if os.environ.get('ES_API_KEY'):
            self.agent.api_key = os.environ['ES_API_KEY']
        
        # S3 bucket
        if os.environ.get('ES_S3_BUCKET'):
            self.backup.s3.bucket = os.environ['ES_S3_BUCKET']
    
    def save(self) -> None:
        """Save current configuration to YAML file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'agent': self._dataclass_to_dict(self.agent),
            'backup': {
                **self._dataclass_to_dict(self.backup),
                's3': self._dataclass_to_dict(self.backup.s3)
            },
            'usb_control': self._dataclass_to_dict(self.usb),
            'network': self._dataclass_to_dict(self.network),
            'data_detection': self._dataclass_to_dict(self.data_detection),
            'logging': self._dataclass_to_dict(self.logging)
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def _dataclass_to_dict(self, obj: Any) -> Dict:
        """Convert a dataclass to dictionary."""
        result = {}
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name)
            # Skip nested dataclasses (handled separately)
            if hasattr(value, '__dataclass_fields__'):
                continue
            result[field_name] = value
        return result
    
    def get_s3_prefix(self) -> str:
        """Get the S3 prefix with placeholders replaced."""
        prefix = self.backup.s3.prefix
        prefix = prefix.replace('{machine_id}', self.agent.machine_id)
        prefix = prefix.replace('{date}', datetime.now().strftime('%Y-%m-%d'))
        prefix = prefix.replace('{hostname}', self.agent.hostname)
        return prefix
    
    def is_path_excluded(self, path: str) -> bool:
        """Check if a path should be excluded from backup."""
        path_lower = path.lower()
        
        for exclude in self.backup.exclude_paths:
            exclude_lower = exclude.lower()
            
            # Handle wildcards
            if '*' in exclude_lower:
                # Convert glob pattern to simple check
                if exclude_lower.startswith('*'):
                    pattern = exclude_lower[1:]
                    if pattern in path_lower:
                        return True
                elif exclude_lower.endswith('*'):
                    pattern = exclude_lower[:-1]
                    if path_lower.startswith(pattern):
                        return True
            else:
                # Exact prefix match
                if path_lower.startswith(exclude_lower):
                    return True
        
        return False
    
    def is_file_excluded(self, filename: str) -> bool:
        """Check if a filename matches exclusion patterns."""
        filename_lower = filename.lower()
        
        for pattern in self.backup.exclude_patterns:
            pattern_lower = pattern.lower()
            
            if pattern_lower.startswith('*'):
                # Extension match
                if filename_lower.endswith(pattern_lower[1:]):
                    return True
            elif pattern_lower.endswith('*'):
                # Prefix match
                if filename_lower.startswith(pattern_lower[:-1]):
                    return True
            else:
                # Exact match
                if filename_lower == pattern_lower:
                    return True
        
        return False


# Global configuration instance
_config: Optional[Config] = None


def get_config(config_path: Optional[Path] = None) -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reload_config() -> Config:
    """Reload configuration from file."""
    global _config
    _config = None
    return get_config()
