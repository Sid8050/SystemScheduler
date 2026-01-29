"""
Database Models for Dashboard Backend

SQLAlchemy models for:
- Endpoints (registered agents)
- Events (security events from agents)
- Policies (configuration templates)
- Users (dashboard users)
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    ForeignKey, JSON, Float, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import enum


Base = declarative_base()


class EndpointStatus(str, enum.Enum):
    """Status of an endpoint."""
    ONLINE = "online"
    OFFLINE = "offline"
    WARNING = "warning"
    ERROR = "error"


class EventSeverity(str, enum.Enum):
    """Severity levels for events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Endpoint(Base):
    """Registered endpoint (agent)."""
    __tablename__ = "endpoints"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(String(100), unique=True, nullable=False, index=True)
    hostname = Column(String(255), nullable=False)
    api_key = Column(String(64), unique=True, nullable=False)
    
    # Status
    status = Column(SQLEnum(EndpointStatus), default=EndpointStatus.OFFLINE)
    last_seen = Column(DateTime, default=datetime.utcnow)
    agent_version = Column(String(20))
    
    # System info
    os_version = Column(String(100))
    ip_address = Column(String(45))
    
    # Configuration
    config = Column(JSON, default={})
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=True)
    
    # Stats
    total_files_backed_up = Column(Integer, default=0)
    total_backup_size = Column(Float, default=0)  # In bytes
    usb_events_count = Column(Integer, default=0)
    network_blocks_count = Column(Integer, default=0)
    sensitive_data_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    events = relationship("Event", back_populates="endpoint", lazy="dynamic")
    policy = relationship("Policy", back_populates="endpoints")
    
    def to_dict(self):
        return {
            "id": self.id,
            "machine_id": self.machine_id,
            "hostname": self.hostname,
            "status": self.status.value if self.status else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "agent_version": self.agent_version,
            "os_version": self.os_version,
            "ip_address": self.ip_address,
            "policy_id": self.policy_id,
            "stats": {
                "files_backed_up": self.total_files_backed_up,
                "backup_size": self.total_backup_size,
                "usb_events": self.usb_events_count,
                "network_blocks": self.network_blocks_count,
                "sensitive_data": self.sensitive_data_count
            }
        }


class Event(Base):
    """Security event from an endpoint."""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False, index=True)
    
    # Event info
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(SQLEnum(EventSeverity), default=EventSeverity.INFO, index=True)
    message = Column(Text)
    details = Column(JSON, default={})
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, index=True)
    received_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    endpoint = relationship("Endpoint", back_populates="events")
    
    # Indexes
    __table_args__ = (
        Index('idx_events_endpoint_timestamp', 'endpoint_id', 'timestamp'),
        Index('idx_events_type_severity', 'event_type', 'severity'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "endpoint_id": self.endpoint_id,
            "event_type": self.event_type,
            "severity": self.severity.value if self.severity else None,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class Policy(Base):
    """Configuration policy template."""
    __tablename__ = "policies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    
    # Policy configuration (matches agent config structure)
    config = Column(JSON, nullable=False, default={
        "files": {"enabled": True, "scan_paths": ["C:\\Users"]},
        "usb": {"mode": "monitor"},
        "network": {"blocked_sites": []},
        "uploads": {"block_all": False, "whitelist": []}
    })
    
    # Metadata
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    endpoints = relationship("Endpoint", back_populates="policy")
    
    def to_dict(self):
        # Handle lazy loading issues in async context
        try:
            endpoint_count = len(self.endpoints)
        except (AttributeError, Exception):
            endpoint_count = 0

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "config": self.config,
            "is_default": self.is_default,
            "endpoint_count": endpoint_count
        }


class User(Base):
    """Dashboard user."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(100))
    role = Column(String(20), default="viewer")  # admin, editor, viewer
    
    # Status
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }


class BlockedSite(Base):
    """Global blocked site."""
    __tablename__ = "blocked_sites"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    category = Column(String(50), index=True)
    reason = Column(Text)
    added_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "domain": self.domain,
            "category": self.category,
            "reason": self.reason
        }


class USBWhitelist(Base):
    """Global USB device whitelist."""
    __tablename__ = "usb_whitelist"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(String(10), nullable=False)
    product_id = Column(String(10), nullable=False)
    serial_number = Column(String(100))
    description = Column(String(255))
    added_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            "serial_number": self.serial_number,
            "description": self.description
        }


class UploadRequest(Base):
    """Workflow for file upload approvals."""
    __tablename__ = "upload_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False)
    
    # File Info
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_hash = Column(String(64), nullable=False, index=True) # SHA-256
    file_size = Column(Integer) # Bytes
    
    # Request Info
    justification = Column(Text)
    destination_site = Column(String(255))
    status = Column(String(20), default="pending") # pending, approved, denied, expired
    
    # Workflow
    requested_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime)
    
    # Relationships
    endpoint = relationship("Endpoint")
    reviewer = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "endpoint_id": self.endpoint_id,
            "hostname": self.endpoint.hostname if self.endpoint else "Unknown",
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "justification": self.justification,
            "destination_site": self.destination_site,
            "status": self.status,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewer_name": self.reviewer.username if self.reviewer else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


# Database setup
DATABASE_URL = "sqlite+aiosqlite:///./dashboard.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Get database session."""
    async with async_session() as session:
        yield session
