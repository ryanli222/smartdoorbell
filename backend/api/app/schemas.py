"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


# --- Event Schemas ---

class EventStartResponse(BaseModel):
    """Response from POST /v1/events/start"""
    event_id: UUID
    upload_url: str

    class Config:
        from_attributes = True


class EventFinalizeRequest(BaseModel):
    """Request body for POST /v1/events/{event_id}/finalize"""
    snapshot_url: str


class EventFinalizeResponse(BaseModel):
    """Response from POST /v1/events/{event_id}/finalize"""
    event_id: UUID
    status: str
    snapshot_url: str

    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    """Full event response"""
    id: UUID
    device_id: UUID
    started_at: datetime
    snapshot_url: Optional[str] = None

    class Config:
        from_attributes = True


# --- Device Schemas ---

class DeviceCreate(BaseModel):
    """Request body for creating a device"""
    name: str


class DeviceResponse(BaseModel):
    """Device response"""
    id: UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True
