"""
Database initialization script.

Creates tables and optionally seeds with test data.
"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal, Base
from app.models import Device, Event


def init_database():
    """Create all tables."""
    print("[Init] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("[Init] Tables created successfully!")


def create_test_device():
    """Create a test device for development."""
    db = SessionLocal()
    try:
        # Check if device already exists
        existing = db.query(Device).filter(Device.name == "test-device").first()
        if existing:
            print(f"[Init] Test device already exists: {existing.id}")
            return existing
        
        # Create test device
        device = Device(name="test-device")
        db.add(device)
        db.commit()
        db.refresh(device)
        
        print(f"[Init] Created test device:")
        print(f"       ID: {device.id}")
        print(f"       Name: {device.name}")
        
        return device
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("Smart Doorbell - Database Initialization")
    print("=" * 50)
    print()
    
    init_database()
    print()
    create_test_device()
    
    print()
    print("[Init] Done!")
