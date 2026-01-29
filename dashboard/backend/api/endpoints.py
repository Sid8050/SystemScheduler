"""
API Endpoints for Dashboard Backend

REST API for:
- Endpoint (agent) management
- Event ingestion and querying
- Policy management
- Dashboard statistics
"""

from datetime import datetime, timedelta
from typing import List, Optional
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from ..models.database import (
    get_db, Endpoint, Event, Policy, BlockedSite, USBWhitelist,
    EndpointStatus, EventSeverity
)


router = APIRouter()


# Pydantic models for request/response
class EndpointRegister(BaseModel):
    """Request to register a new endpoint."""
    machine_id: str
    hostname: str
    agent_version: Optional[str] = None
    os_version: Optional[str] = None
    ip_address: Optional[str] = None


class EndpointResponse(BaseModel):
    """Response for endpoint registration."""
    id: int
    machine_id: str
    api_key: str
    config: dict


class EventSubmit(BaseModel):
    """Submit events from agent."""
    events: List[dict]


class HeartbeatRequest(BaseModel):
    """Heartbeat from agent."""
    status: str
    stats: Optional[dict] = None


class PolicyCreate(BaseModel):
    """Create a new policy."""
    name: str
    description: Optional[str] = None
    config: dict


class BlockedSiteCreate(BaseModel):
    """Add a blocked site."""
    domain: str
    category: Optional[str] = None
    reason: Optional[str] = None


class USBWhitelistCreate(BaseModel):
    """Add USB device to whitelist."""
    vendor_id: str
    product_id: str
    serial_number: Optional[str] = None
    description: Optional[str] = None


# Authentication helpers
async def verify_api_key(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> Endpoint:
    """Verify API key and return endpoint."""
    result = await db.execute(
        select(Endpoint).where(Endpoint.api_key == x_api_key)
    )
    endpoint = result.scalar_one_or_none()
    
    if not endpoint:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return endpoint


# Endpoint management
@router.post("/endpoints/register", response_model=EndpointResponse)
async def register_endpoint(
    data: EndpointRegister,
    db: AsyncSession = Depends(get_db)
):
    """Register a new endpoint (agent)."""
    # Check if already registered
    result = await db.execute(
        select(Endpoint).where(Endpoint.machine_id == data.machine_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Update existing endpoint
        existing.hostname = data.hostname
        existing.agent_version = data.agent_version
        existing.os_version = data.os_version
        existing.ip_address = data.ip_address
        existing.status = EndpointStatus.ONLINE
        existing.last_seen = datetime.utcnow()
        await db.commit()
        
        return EndpointResponse(
            id=existing.id,
            machine_id=existing.machine_id,
            api_key=existing.api_key,
            config=existing.config or {}
        )
    
    # Create new endpoint
    api_key = secrets.token_urlsafe(32)
    
    endpoint = Endpoint(
        machine_id=data.machine_id,
        hostname=data.hostname,
        api_key=api_key,
        agent_version=data.agent_version,
        os_version=data.os_version,
        ip_address=data.ip_address,
        status=EndpointStatus.ONLINE,
        last_seen=datetime.utcnow()
    )
    
    # Get default policy config
    result = await db.execute(
        select(Policy).where(Policy.is_default == True)
    )
    default_policy = result.scalar_one_or_none()
    if default_policy:
        endpoint.policy_id = default_policy.id
        endpoint.config = default_policy.config
    
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)
    
    return EndpointResponse(
        id=endpoint.id,
        machine_id=endpoint.machine_id,
        api_key=api_key,
        config=endpoint.config or {}
    )


@router.get("/endpoints")
async def list_endpoints(
    status: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all registered endpoints."""
    query = select(Endpoint)
    
    if status:
        query = query.where(Endpoint.status == EndpointStatus(status))
    
    query = query.order_by(desc(Endpoint.last_seen)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    endpoints = result.scalars().all()
    
    # Count total
    count_result = await db.execute(select(func.count(Endpoint.id)))
    total = count_result.scalar()
    
    return {
        "endpoints": [e.to_dict() for e in endpoints],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/endpoints/{endpoint_id}")
async def get_endpoint(
    endpoint_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get endpoint details."""
    result = await db.execute(
        select(Endpoint).where(Endpoint.id == endpoint_id)
    )
    endpoint = result.scalar_one_or_none()
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return endpoint.to_dict()


@router.delete("/endpoints/{endpoint_id}")
async def delete_endpoint(
    endpoint_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete an endpoint."""
    result = await db.execute(
        select(Endpoint).where(Endpoint.id == endpoint_id)
    )
    endpoint = result.scalar_one_or_none()
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    await db.delete(endpoint)
    await db.commit()
    
    return {"status": "deleted"}


async def get_merged_config(endpoint: Endpoint, db: AsyncSession) -> dict:
    """Get the latest configuration for an endpoint, merging global settings."""
    # Start with base template to ensure all keys exist
    config = {
        "files": {"enabled": True, "scan_paths": ["C:\\Users"]},
        "usb": {"mode": "monitor", "whitelist": []},
        "network": {"blocked_sites": []},
        "uploads": {"block_all": False, "whitelist": []}
    }
    
    # Override with fresh config from the assigned policy
    if endpoint.policy_id:
        result = await db.execute(
            select(Policy).where(Policy.id == endpoint.policy_id)
        )
        policy = result.scalar_one_or_none()
        if policy and policy.config:
            # Deep merge policy config into template
            for key, val in policy.config.items():
                if key in config and isinstance(config[key], dict) and isinstance(val, dict):
                    config[key].update(val)
                else:
                    config[key] = val
    
    # Merge global blocked sites
    result = await db.execute(select(BlockedSite))
    blocked_sites = result.scalars().all()
    global_blocked = [s.domain for s in blocked_sites]
    config['network']['blocked_sites'] = list(set(config['network'].get('blocked_sites', []) + global_blocked))
    
    # Merge global USB whitelist
    result = await db.execute(select(USBWhitelist))
    usb_whitelist = result.scalars().all()
    global_whitelist = [
        {'vid': d.vendor_id, 'pid': d.product_id, 'serial': d.serial_number, 'description': d.description}
        for d in usb_whitelist
    ]
    config['usb']['whitelist'] = config['usb'].get('whitelist', []) + global_whitelist
    
    return config


# Agent API (requires API key)
@router.post("/agent/heartbeat")
async def agent_heartbeat(
    data: HeartbeatRequest,
    endpoint: Endpoint = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Receive heartbeat from agent."""
    endpoint.status = EndpointStatus.ONLINE
    endpoint.last_seen = datetime.utcnow()
    
    if data.stats:
        if 'files_backed_up' in data.stats:
            endpoint.total_files_backed_up = data.stats['files_backed_up']
        if 'backup_size' in data.stats:
            endpoint.total_backup_size = data.stats['backup_size']
    
    await db.commit()
    
    # Return merged config
    config = await get_merged_config(endpoint, db)
    
    return {
        "status": "ok",
        "config": config
    }


@router.post("/agent/events")
async def submit_events(
    data: EventSubmit,
    endpoint: Endpoint = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Submit events from agent."""
    events_created = 0
    
    for event_data in data.events:
        event = Event(
            endpoint_id=endpoint.id,
            event_type=event_data.get('event_type', 'unknown'),
            severity=EventSeverity(event_data.get('severity', 'info')),
            message=event_data.get('message', ''),
            details=event_data.get('details', {}),
            timestamp=datetime.fromisoformat(event_data['timestamp'].replace('Z', '+00:00'))
            if 'timestamp' in event_data else datetime.utcnow()
        )
        db.add(event)
        events_created += 1
        
        # Update endpoint stats
        if 'usb' in event.event_type:
            endpoint.usb_events_count += 1
        elif 'net.blocked' in event.event_type:
            endpoint.network_blocks_count += 1
        elif 'data.sensitive' in event.event_type:
            endpoint.sensitive_data_count += 1
    
    await db.commit()
    
    return {"status": "ok", "events_received": events_created}


@router.get("/agent/config")
async def get_agent_config(
    endpoint: Endpoint = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Get configuration for agent."""
    return await get_merged_config(endpoint, db)


# Events API
@router.get("/events")
async def list_events(
    endpoint_id: Optional[int] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List security events."""
    query = select(Event)
    
    filters = []
    if endpoint_id:
        filters.append(Event.endpoint_id == endpoint_id)
    if event_type:
        filters.append(Event.event_type.like(f"%{event_type}%"))
    if severity:
        filters.append(Event.severity == EventSeverity(severity))
    if since:
        filters.append(Event.timestamp >= since)
    if until:
        filters.append(Event.timestamp <= until)
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.order_by(desc(Event.timestamp)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return {
        "events": [e.to_dict() for e in events],
        "limit": limit,
        "offset": offset
    }


@router.get("/events/stats")
async def get_event_stats(
    hours: int = Query(24, le=168),  # Max 1 week
    db: AsyncSession = Depends(get_db)
):
    """Get event statistics."""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Count by severity
    severity_result = await db.execute(
        select(Event.severity, func.count(Event.id))
        .where(Event.timestamp >= since)
        .group_by(Event.severity)
    )
    by_severity = {row[0].value: row[1] for row in severity_result}
    
    # Count by type
    type_result = await db.execute(
        select(Event.event_type, func.count(Event.id))
        .where(Event.timestamp >= since)
        .group_by(Event.event_type)
        .order_by(desc(func.count(Event.id)))
        .limit(10)
    )
    by_type = {row[0]: row[1] for row in type_result}
    
    # Total count
    total_result = await db.execute(
        select(func.count(Event.id)).where(Event.timestamp >= since)
    )
    total = total_result.scalar()
    
    return {
        "period_hours": hours,
        "total_events": total,
        "by_severity": by_severity,
        "by_type": by_type
    }


# Policy management
@router.get("/policies")
async def list_policies(db: AsyncSession = Depends(get_db)):
    """List all policies."""
    result = await db.execute(
        select(Policy).options(selectinload(Policy.endpoints))
    )
    policies = result.scalars().all()
    
    return {"policies": [p.to_dict() for p in policies]}


from sqlalchemy.exc import IntegrityError

# ... (rest of imports)

@router.post("/policies")
async def create_policy(
    data: PolicyCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new policy."""
    try:
        policy = Policy(
            name=data.name,
            description=data.description,
            config=data.config
        )
        
        db.add(policy)
        await db.commit()
        await db.refresh(policy)
        
        return policy.to_dict()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Policy with name '{data.name}' already exists")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/policies/{policy_id}")
async def update_policy(
    policy_id: int,
    data: PolicyCreate,
    db: AsyncSession = Depends(get_db)
):
    """Update a policy."""
    result = await db.execute(
        select(Policy).options(selectinload(Policy.endpoints)).where(Policy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    try:
        policy.name = data.name
        policy.description = data.description
        policy.config = data.config
        
        await db.commit()
        return policy.to_dict()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Policy with name '{data.name}' already exists")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/policies/{policy_id}/apply/{endpoint_id}")
async def apply_policy(
    policy_id: int,
    endpoint_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Apply policy to endpoint."""
    policy_result = await db.execute(
        select(Policy).where(Policy.id == policy_id)
    )
    policy = policy_result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    endpoint_result = await db.execute(
        select(Endpoint).where(Endpoint.id == endpoint_id)
    )
    endpoint = endpoint_result.scalar_one_or_none()
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    endpoint.policy_id = policy_id
    endpoint.config = policy.config
    
    await db.commit()
    
    return {"status": "applied"}


# Blocked sites
@router.get("/blocked-sites")
async def list_blocked_sites(db: AsyncSession = Depends(get_db)):
    """List all blocked sites."""
    result = await db.execute(select(BlockedSite))
    sites = result.scalars().all()
    
    return {"sites": [s.to_dict() for s in sites]}


@router.post("/blocked-sites")
async def add_blocked_site(
    data: BlockedSiteCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a blocked site."""
    site = BlockedSite(
        domain=data.domain.lower(),
        category=data.category,
        reason=data.reason
    )
    
    db.add(site)
    await db.commit()
    await db.refresh(site)
    
    return site.to_dict()


@router.delete("/blocked-sites/{site_id}")
async def remove_blocked_site(
    site_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove a blocked site."""
    result = await db.execute(
        select(BlockedSite).where(BlockedSite.id == site_id)
    )
    site = result.scalar_one_or_none()
    
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    await db.delete(site)
    await db.commit()
    
    return {"status": "deleted"}


# USB whitelist
@router.get("/usb-whitelist")
async def list_usb_whitelist(db: AsyncSession = Depends(get_db)):
    """List USB whitelist."""
    result = await db.execute(select(USBWhitelist))
    devices = result.scalars().all()
    
    return {"devices": [d.to_dict() for d in devices]}


@router.post("/usb-whitelist")
async def add_usb_whitelist(
    data: USBWhitelistCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add device to USB whitelist."""
    device = USBWhitelist(
        vendor_id=data.vendor_id.upper(),
        product_id=data.product_id.upper(),
        serial_number=data.serial_number,
        description=data.description
    )
    
    db.add(device)
    await db.commit()
    await db.refresh(device)
    
    return device.to_dict()


@router.delete("/usb-whitelist/{device_id}")
async def remove_usb_whitelist(
    device_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove device from USB whitelist."""
    result = await db.execute(
        select(USBWhitelist).where(USBWhitelist.id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await db.delete(device)
    await db.commit()
    
    return {"status": "deleted"}


# Dashboard stats
@router.get("/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard overview statistics."""
    # Endpoint counts
    total_endpoints = await db.execute(select(func.count(Endpoint.id)))
    online_endpoints = await db.execute(
        select(func.count(Endpoint.id)).where(Endpoint.status == EndpointStatus.ONLINE)
    )
    
    # Event counts (last 24h)
    since = datetime.utcnow() - timedelta(hours=24)
    event_count = await db.execute(
        select(func.count(Event.id)).where(Event.timestamp >= since)
    )
    
    critical_events = await db.execute(
        select(func.count(Event.id)).where(
            and_(
                Event.timestamp >= since,
                Event.severity == EventSeverity.CRITICAL
            )
        )
    )
    
    # Aggregate stats
    total_backed_up = await db.execute(
        select(func.sum(Endpoint.total_files_backed_up))
    )
    total_size = await db.execute(
        select(func.sum(Endpoint.total_backup_size))
    )
    
    return {
        "endpoints": {
            "total": total_endpoints.scalar() or 0,
            "online": online_endpoints.scalar() or 0
        },
        "events_24h": {
            "total": event_count.scalar() or 0,
            "critical": critical_events.scalar() or 0
        },
        "backup": {
            "total_files": total_backed_up.scalar() or 0,
            "total_size_bytes": total_size.scalar() or 0
        }
    }
