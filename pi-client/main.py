"""
Smart Doorbell - Pi Client Main Application

Detects motion via camera, captures snapshot, uploads to backend.
"""

import os
import sys
import time
import json
import uuid
import requests
from datetime import datetime
from doorcam.camera_motion import CameraMotionDetector
from doorcam.camera_manager import CameraManager


# Configuration from environment
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEVICE_ID = os.getenv("DEVICE_ID", "doorcam-01")
API_KEY = os.getenv("API_KEY", "dev-secret-key-12345")


class DoorbellClient:
    """Main doorbell client that ties everything together."""
    
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.device_id = DEVICE_ID
        self.api_key = API_KEY
        
        self.camera = CameraManager()
        self.detector = CameraMotionDetector(
            callback=self.on_motion_detected,
            camera_index=0,
            sensitivity=25,
            min_area=5000,
            cooldown_sec=5.0
        )
        
        self.event_count = 0
    
    def on_motion_detected(self):
        """Called when motion is detected."""
        self.event_count += 1
        print(f"\n{'='*50}")
        print(f"[Event #{self.event_count}] Motion detected at {datetime.now().isoformat()}")
        
        # Capture snapshot
        print("[1/4] Capturing snapshot...")
        snapshot_data = self.camera.capture_snapshot()
        if not snapshot_data:
            print("ERROR: Failed to capture snapshot")
            return
        print(f"      Captured {len(snapshot_data)} bytes")
        
        # Start event with backend
        print("[2/4] Starting event with backend...")
        event_data = self.start_event()
        if not event_data:
            print("ERROR: Failed to start event - saving locally")
            self.save_locally(snapshot_data)
            return
        
        event_id = event_data.get("event_id")
        upload_url = event_data.get("upload_url")
        object_key = event_data.get("object_key")
        print(f"      Event ID: {event_id}")
        
        # Upload snapshot to MinIO
        print("[3/4] Uploading snapshot...")
        if not self.upload_snapshot(upload_url, snapshot_data):
            print("ERROR: Failed to upload snapshot")
            self.save_locally(snapshot_data, event_id)
            return
        print("      Upload complete!")
        
        # Finalize event
        print("[4/4] Finalizing event...")
        if self.finalize_event(event_id, object_key):
            print("      Event finalized successfully!")
        else:
            print("ERROR: Failed to finalize event")
        
        print(f"{'='*50}\n")
    
    def start_event(self) -> dict:
        """Start a new event with the backend."""
        try:
            response = requests.post(
                f"{self.backend_url}/v1/events/start",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "device_id": self.device_id,
                    "started_at": datetime.utcnow().isoformat() + "Z"
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"      Error: {e}")
            return None
    
    def upload_snapshot(self, upload_url: str, data: bytes) -> bool:
        """Upload snapshot to presigned URL."""
        try:
            response = requests.put(
                upload_url,
                data=data,
                headers={"Content-Type": "image/jpeg"},
                timeout=30
            )
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"      Upload error: {e}")
            return False
    
    def finalize_event(self, event_id: str, object_key: str) -> bool:
        """Finalize the event with the backend."""
        try:
            response = requests.post(
                f"{self.backend_url}/v1/events/{event_id}/finalize",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={"snapshot_object_key": object_key},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"      Finalize error: {e}")
            return False
    
    def save_locally(self, data: bytes, event_id: str = None):
        """Save snapshot locally if upload fails."""
        if not event_id:
            event_id = str(uuid.uuid4())
        
        os.makedirs("spool", exist_ok=True)
        filename = f"spool/{event_id}.jpg"
        with open(filename, "wb") as f:
            f.write(data)
        print(f"      Saved locally: {filename}")
    
    def run(self, show_preview: bool = True):
        """Run the doorbell client."""
        print("=" * 50)
        print("Smart Doorbell - Pi Client")
        print("=" * 50)
        print(f"Backend: {self.backend_url}")
        print(f"Device:  {self.device_id}")
        print()
        
        # Open camera for snapshots
        if not self.camera.open():
            print("ERROR: Failed to open camera for snapshots")
            return
        
        print("Starting motion detection...")
        print("Press 'q' in preview window to quit (or Ctrl+C)")
        print()
        
        try:
            self.detector.start(show_preview=show_preview)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.detector.stop()
            self.camera.close()
            print(f"\nTotal events captured: {self.event_count}")


def main():
    # Check for command line args
    show_preview = "--no-preview" not in sys.argv
    
    client = DoorbellClient()
    client.run(show_preview=show_preview)


if __name__ == "__main__":
    main()
