"""
SQLAlchemy database models.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class Device(Base):
    """Device registered in the system."""
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    api_key_hash = Column(String(255), nullable=True)  # Optional for now
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    events = relationship("Event", back_populates="device")

    def __repr__(self):
        return f"<Device {self.name}>"


class Event(Base):
    """Motion detection event from a device."""
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    snapshot_url = Column(Text, nullable=True)  # Filled on finalize

    # Relationships
    device = relationship("Device", back_populates="events")

    def __repr__(self):
        return f"<Event {self.id}>"
