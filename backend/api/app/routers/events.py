"""
Events API router.

Endpoints:
- POST /v1/events/start - Start a new event, get presigned upload URL
- POST /v1/events/{event_id}/finalize - Finalize event with snapshot URL
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import Device, Event
from ..schemas import EventStartResponse, EventFinalizeRequest, EventFinalizeResponse, EventResponse
from ..storage import storage

router = APIRouter(prefix="/v1/events", tags=["events"])


@router.post("/start", response_model=EventStartResponse)
def start_event(
    device_id: Optional[str] = Query(None, description="Device ID (optional, uses default if not provided)"),
    db: Session = Depends(get_db)
):
    """
    Start a new motion detection event.
    
    Returns an event ID and a presigned URL for uploading the snapshot.
    """
    # Get or create a default device if none specified
    if device_id:
        try:
            device_uuid = uuid.UUID(device_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid device_id format")
        
        device = db.query(Device).filter(Device.id == device_uuid).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
    else:
        # Use or create default device
        device = db.query(Device).filter(Device.name == "default").first()
        if not device:
            device = Device(name="default")
            db.add(device)
            db.commit()
            db.refresh(device)
    
    # Create new event
    event = Event(
        device_id=device.id,
        started_at=datetime.utcnow()
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # Generate presigned upload URL
    object_name = f"snapshots/{event.id}.jpg"
    upload_url = storage.generate_presigned_upload_url(object_name)
    
    return EventStartResponse(
        event_id=event.id,
        upload_url=upload_url
    )


@router.post("/{event_id}/finalize", response_model=EventFinalizeResponse)
def finalize_event(
    event_id: str,
    request: EventFinalizeRequest,
    db: Session = Depends(get_db)
):
    """
    Finalize an event after the snapshot has been uploaded.
    
    Updates the event with the snapshot URL.
    """
    try:
        event_uuid = uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event_id format")
    
    event = db.query(Event).filter(Event.id == event_uuid).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update snapshot URL
    event.snapshot_url = request.snapshot_url
    db.commit()
    db.refresh(event)
    
    return EventFinalizeResponse(
        event_id=event.id,
        status="finalized",
        snapshot_url=event.snapshot_url
    )


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: str,
    db: Session = Depends(get_db)
):
    """Get an event by ID."""
    try:
        event_uuid = uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event_id format")
    
    event = db.query(Event).filter(Event.id == event_uuid).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return event


@router.get("/", response_model=list[EventResponse])
def list_events(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List recent events."""
    events = db.query(Event).order_by(Event.started_at.desc()).limit(limit).all()
    return events
