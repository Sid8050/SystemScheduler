"""
Centralized Logging for Endpoint Security Agent

Provides structured logging with support for:
- Local file logging with rotation
- JSON format for parsing
- Dashboard sync
- S3 backup of logs
"""

import os
import sys
import json
import queue
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from dataclasses import dataclass, asdict
from enum import Enum


class EventType(str, Enum):
    """Types of security events."""
    # File events
    FILE_CREATED = "file.created"
    FILE_MODIFIED = "file.modified"
    FILE_DELETED = "file.deleted"
    FILE_BACKED_UP = "file.backed_up"
    FILE_BACKUP_FAILED = "file.backup_failed"
    
    # USB events
    USB_CONNECTED = "usb.connected"
    USB_DISCONNECTED = "usb.disconnected"
    USB_BLOCKED = "usb.blocked"
    USB_FILE_COPY = "usb.file_copy"
    
    # Network events
    NET_CONNECTION = "net.connection"
    NET_BLOCKED = "net.blocked"
    NET_DNS_QUERY = "net.dns_query"
    
    # Data detection events
    DATA_SENSITIVE_FOUND = "data.sensitive_found"
    DATA_UPLOAD_BLOCKED = "data.upload_blocked"
    
    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"
    AGENT_CONFIG_CHANGED = "agent.config_changed"
    
    # System events
    SYSTEM_INFO = "system.info"
    SYSTEM_WARNING = "system.warning"
    SYSTEM_ERROR = "system.error"


@dataclass
class SecurityEvent:
    """Structured security event."""
    timestamp: str
    event_type: str
    severity: str  # info, warning, error, critical
    machine_id: str
    hostname: str
    message: str
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields
        if hasattr(record, 'event_type'):
            log_data['event_type'] = record.event_type
        if hasattr(record, 'details'):
            log_data['details'] = record.details
        if hasattr(record, 'machine_id'):
            log_data['machine_id'] = record.machine_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class EventBuffer:
    """Buffer for events to be synced to dashboard."""
    
    def __init__(self, max_size: int = 1000):
        self.events: List[SecurityEvent] = []
        self.max_size = max_size
        self._lock = threading.Lock()
    
    def add(self, event: SecurityEvent) -> None:
        with self._lock:
            self.events.append(event)
            # Keep buffer from growing too large
            if len(self.events) > self.max_size:
                self.events = self.events[-self.max_size:]
    
    def get_and_clear(self) -> List[SecurityEvent]:
        with self._lock:
            events = self.events.copy()
            self.events.clear()
            return events
    
    def __len__(self) -> int:
        return len(self.events)


class Logger:
    """
    Centralized logger for the Endpoint Security Agent.
    
    Provides:
    - Standard Python logging
    - Structured security events
    - Event buffering for dashboard sync
    - File rotation
    """
    
    def __init__(
        self,
        name: str = "EndpointSecurity",
        log_dir: Optional[Path] = None,
        level: str = "INFO",
        max_size_mb: int = 100,
        backup_count: int = 5,
        machine_id: str = "",
        hostname: str = ""
    ):
        self.name = name
        self.log_dir = log_dir or Path("C:/ProgramData/EndpointSecurity/logs")
        self.level = getattr(logging, level.upper(), logging.INFO)
        self.max_size_mb = max_size_mb
        self.backup_count = backup_count
        self.machine_id = machine_id
        self.hostname = hostname
        
        # Event buffer for dashboard sync
        self.event_buffer = EventBuffer()
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Setup logging handlers."""
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Get root logger for our namespace
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler (human readable)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (JSON format, rotating)
        log_file = self.log_dir / f"{self.name.lower()}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_size_mb * 1024 * 1024,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.level)
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)
        
        # Events file (security events only)
        events_file = self.log_dir / "events.jsonl"
        self.events_handler = RotatingFileHandler(
            events_file,
            maxBytes=self.max_size_mb * 1024 * 1024,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        self.events_handler.setLevel(logging.INFO)
        self.events_handler.setFormatter(JSONFormatter())
    
    def _create_event(
        self,
        event_type: EventType,
        message: str,
        severity: str = "info",
        details: Optional[Dict] = None
    ) -> SecurityEvent:
        """Create a structured security event."""
        return SecurityEvent(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            event_type=event_type.value,
            severity=severity,
            machine_id=self.machine_id,
            hostname=self.hostname,
            message=message,
            details=details or {}
        )
    
    def log_event(
        self,
        event_type: EventType,
        message: str,
        severity: str = "info",
        details: Optional[Dict] = None
    ) -> SecurityEvent:
        """Log a security event."""
        event = self._create_event(event_type, message, severity, details)
        
        # Write to events file
        self.events_handler.stream.write(event.to_json() + '\n')
        self.events_handler.stream.flush()
        
        # Add to buffer for dashboard sync
        self.event_buffer.add(event)
        
        # Also log to main logger
        log_level = {
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }.get(severity, logging.INFO)
        
        self.logger.log(
            log_level,
            f"[{event_type.value}] {message}",
            extra={'event_type': event_type.value, 'details': details}
        )
        
        return event
    
    # Convenience methods for common events
    def file_backed_up(self, path: str, size: int, s3_key: str) -> SecurityEvent:
        return self.log_event(
            EventType.FILE_BACKED_UP,
            f"File backed up: {path}",
            "info",
            {"path": path, "size": size, "s3_key": s3_key}
        )
    
    def file_backup_failed(self, path: str, error: str) -> SecurityEvent:
        return self.log_event(
            EventType.FILE_BACKUP_FAILED,
            f"Backup failed: {path}",
            "error",
            {"path": path, "error": error}
        )
    
    def usb_connected(self, device_info: Dict) -> SecurityEvent:
        return self.log_event(
            EventType.USB_CONNECTED,
            f"USB device connected: {device_info.get('description', 'Unknown')}",
            "info",
            device_info
        )
    
    def usb_blocked(self, device_info: Dict, reason: str) -> SecurityEvent:
        return self.log_event(
            EventType.USB_BLOCKED,
            f"USB device blocked: {device_info.get('description', 'Unknown')}",
            "warning",
            {"device": device_info, "reason": reason}
        )
    
    def usb_file_copy(self, src: str, dst: str, direction: str) -> SecurityEvent:
        return self.log_event(
            EventType.USB_FILE_COPY,
            f"File {'copied to' if direction == 'to' else 'copied from'} USB: {src}",
            "warning",
            {"source": src, "destination": dst, "direction": direction}
        )
    
    def network_blocked(self, domain: str, reason: str, process: Optional[str] = None) -> SecurityEvent:
        return self.log_event(
            EventType.NET_BLOCKED,
            f"Network blocked: {domain}",
            "warning",
            {"domain": domain, "reason": reason, "process": process}
        )
    
    def sensitive_data_found(self, path: str, data_type: str, count: int) -> SecurityEvent:
        return self.log_event(
            EventType.DATA_SENSITIVE_FOUND,
            f"Sensitive data found in {path}: {count} {data_type}",
            "warning",
            {"path": path, "data_type": data_type, "count": count}
        )
    
    def agent_started(self) -> SecurityEvent:
        return self.log_event(
            EventType.AGENT_STARTED,
            "Endpoint Security Agent started",
            "info",
            {"version": "1.0.0"}
        )
    
    def agent_stopped(self, reason: str = "normal") -> SecurityEvent:
        return self.log_event(
            EventType.AGENT_STOPPED,
            f"Endpoint Security Agent stopped: {reason}",
            "info",
            {"reason": reason}
        )
    
    def agent_error(self, error: str, module: str) -> SecurityEvent:
        return self.log_event(
            EventType.AGENT_ERROR,
            f"Agent error in {module}: {error}",
            "error",
            {"error": error, "module": module}
        )
    
    # Standard logging methods
    def debug(self, message: str, **kwargs) -> None:
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        self.logger.critical(message, extra=kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        self.logger.exception(message, extra=kwargs)
    
    def get_pending_events(self) -> List[SecurityEvent]:
        """Get buffered events for dashboard sync."""
        return self.event_buffer.get_and_clear()


# Global logger instance
_logger: Optional[Logger] = None


def get_logger(
    name: str = "EndpointSecurity",
    log_dir: Optional[Path] = None,
    **kwargs
) -> Logger:
    """Get or create the global logger instance."""
    global _logger
    if _logger is None:
        _logger = Logger(name=name, log_dir=log_dir, **kwargs)
    return _logger


def setup_logger(config) -> Logger:
    """Setup logger from configuration."""
    global _logger
    _logger = Logger(
        name="EndpointSecurity",
        log_dir=Path(config.logging.local_path),
        level=config.logging.level,
        max_size_mb=config.logging.max_size_mb,
        machine_id=config.agent.machine_id,
        hostname=config.agent.hostname
    )
    return _logger
