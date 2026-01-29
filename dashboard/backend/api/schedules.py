"""
Scheduled Scans API for Dashboard

Manage scheduled backup/scan tasks:
- Create scan schedules
- View schedule status
- Enable/disable schedules
- View scan history
"""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from ..models.database import get_db, Base
from .auth import get_current_user, User
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey


# Schedule model (add to database.py ideally, but keeping here for simplicity)
from sqlalchemy.orm import declarative_base

# We'll use the existing Base from database.py
from ..models.database import Base, engine


class Schedule(Base):
    """Scheduled scan/backup task."""
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    
    # Schedule type: full_scan, incremental_backup, sensitive_scan
    schedule_type = Column(String(50), nullable=False)
    
    # Cron expression (e.g., "0 2 * * *" for daily at 2 AM)
    cron_expression = Column(String(100), nullable=False)
    
    # Target configuration
    target_paths = Column(JSON, default=[])  # Paths to scan
    target_endpoints = Column(JSON, default=[])  # Specific endpoint IDs, empty = all
    
    # Status
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    last_status = Column(String(20))  # success, failed, running
    last_error = Column(String(500))
    
    # Stats
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "schedule_type": self.schedule_type,
            "cron_expression": self.cron_expression,
            "target_paths": self.target_paths,
            "target_endpoints": self.target_endpoints,
            "is_active": self.is_active,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ScheduleRun(Base):
    """History of schedule executions."""
    __tablename__ = "schedule_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    status = Column(String(20))  # running, success, failed
    
    # Results
    files_scanned = Column(Integer, default=0)
    files_backed_up = Column(Integer, default=0)
    sensitive_found = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    
    # Details
    error_message = Column(String(500))
    details = Column(JSON, default={})
    
    def to_dict(self):
        return {
            "id": self.id,
            "schedule_id": self.schedule_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "files_scanned": self.files_scanned,
            "files_backed_up": self.files_backed_up,
            "sensitive_found": self.sensitive_found,
            "errors_count": self.errors_count,
            "error_message": self.error_message,
        }


router = APIRouter()


# Pydantic models
class ScheduleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    schedule_type: str  # full_scan, incremental_backup, sensitive_scan
    cron_expression: str
    target_paths: List[str] = []
    target_endpoints: List[int] = []


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    target_paths: Optional[List[str]] = None
    target_endpoints: Optional[List[int]] = None
    is_active: Optional[bool] = None


# Common cron presets
CRON_PRESETS = {
    "hourly": "0 * * * *",
    "daily_2am": "0 2 * * *",
    "daily_midnight": "0 0 * * *",
    "weekly_sunday": "0 2 * * 0",
    "weekly_monday": "0 2 * * 1",
    "monthly": "0 2 1 * *",
    "every_6_hours": "0 */6 * * *",
    "every_12_hours": "0 */12 * * *",
}


def parse_cron_to_readable(cron: str) -> str:
    """Convert cron expression to human readable format."""
    # Find preset match
    for name, expr in CRON_PRESETS.items():
        if expr == cron:
            return name.replace("_", " ").title()
    
    parts = cron.split()
    if len(parts) != 5:
        return cron
    
    minute, hour, day, month, weekday = parts
    
    if minute == "0" and hour != "*" and day == "*" and month == "*" and weekday == "*":
        return f"Daily at {hour}:00"
    
    return cron


@router.get("/presets")
async def get_schedule_presets():
    """Get available cron presets."""
    return {
        "presets": [
            {"value": v, "label": k.replace("_", " ").title(), "description": parse_cron_to_readable(v)}
            for k, v in CRON_PRESETS.items()
        ]
    }


@router.get("")
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all schedules."""
    result = await db.execute(
        select(Schedule).order_by(desc(Schedule.created_at))
    )
    schedules = result.scalars().all()
    
    return {
        "schedules": [s.to_dict() for s in schedules]
    }


@router.post("")
async def create_schedule(
    data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new schedule."""
    # Validate schedule type
    valid_types = ["full_scan", "incremental_backup", "sensitive_scan", "network_audit"]
    if data.schedule_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid schedule type. Must be one of: {valid_types}")
    
    schedule = Schedule(
        name=data.name,
        description=data.description,
        schedule_type=data.schedule_type,
        cron_expression=data.cron_expression,
        target_paths=data.target_paths,
        target_endpoints=data.target_endpoints,
        created_by=current_user.id
    )
    
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    
    return schedule.to_dict()


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get schedule details."""
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return schedule.to_dict()


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: int,
    data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a schedule."""
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if data.name is not None:
        schedule.name = data.name
    if data.description is not None:
        schedule.description = data.description
    if data.cron_expression is not None:
        schedule.cron_expression = data.cron_expression
    if data.target_paths is not None:
        schedule.target_paths = data.target_paths
    if data.target_endpoints is not None:
        schedule.target_endpoints = data.target_endpoints
    if data.is_active is not None:
        schedule.is_active = data.is_active
    
    await db.commit()
    return schedule.to_dict()


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a schedule."""
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    await db.delete(schedule)
    await db.commit()
    
    return {"status": "deleted"}


@router.post("/{schedule_id}/toggle")
async def toggle_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle schedule active state."""
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedule.is_active = not schedule.is_active
    await db.commit()
    
    return {"is_active": schedule.is_active}


@router.post("/{schedule_id}/run")
async def run_schedule_now(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger immediate schedule run."""
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Create a run record
    run = ScheduleRun(
        schedule_id=schedule_id,
        started_at=datetime.utcnow(),
        status="running"
    )
    
    db.add(run)
    
    # Update schedule
    schedule.last_run = datetime.utcnow()
    schedule.last_status = "running"
    schedule.total_runs += 1
    
    await db.commit()
    
    # In production, this would trigger the actual scan via message queue
    # For now, just return the run info
    return {
        "status": "triggered",
        "run_id": run.id,
        "message": "Scan triggered. Check run history for results."
    }


@router.get("/{schedule_id}/runs")
async def get_schedule_runs(
    schedule_id: int,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get schedule run history."""
    result = await db.execute(
        select(ScheduleRun)
        .where(ScheduleRun.schedule_id == schedule_id)
        .order_by(desc(ScheduleRun.started_at))
        .limit(limit)
    )
    runs = result.scalars().all()
    
    return {"runs": [r.to_dict() for r in runs]}
