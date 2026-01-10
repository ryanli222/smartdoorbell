"""
Smart Doorbell - Pi Client Main Application

Detects motion via camera, captures snapshot, uploads to backend.
Uses base64 upload to avoid presigned URL issues with NAT/ngrok.
"""

import os
import sys
import time
import uuid
import cv2
import base64
import requests
from datetime import datetime
from doorcam.camera_motion import CameraMotionDetector


# Configuration from environment
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEVICE_ID = os.getenv("DEVICE_ID", "doorcam-01")
API_KEY = os.getenv("API_KEY", "dev-secret-key-12345")


class DoorbellClient:
    """Main doorbell client - uses single camera for motion + snapshots."""
    
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.device_id = DEVICE_ID
        self.api_key = API_KEY
        self.event_count = 0
        self._detector = None
    
    def capture_from_detector(self) -> bytes:
        """Capture snapshot from the motion detector's camera."""
        if self._detector and self._detector._cap:
            ret, frame = self._detector._cap.read()
            if ret:
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                return jpeg.tobytes()
        return None
    
    def on_motion_detected(self):
        """Called when motion is detected."""
        self.event_count += 1
        print(f"\n{'='*50}")
        print(f"[Event #{self.event_count}] Motion detected at {datetime.now().isoformat()}")
        
        # Capture snapshot from the same camera
        print("[1/3] Capturing snapshot...")
        snapshot_data = self.capture_from_detector()
        if not snapshot_data:
            print("ERROR: Failed to capture snapshot")
            return
        print(f"      Captured {len(snapshot_data)} bytes")
        
        # Start event with backend  
        print("[2/3] Creating event...")
        event_id = self.create_event()
        if not event_id:
            print("ERROR: Failed to create event - saving locally")
            self.save_locally(snapshot_data)
            return
        print(f"      Event ID: {event_id}")
        
        # Upload snapshot via base64
        print("[3/3] Uploading snapshot...")
        if self.upload_base64(event_id, snapshot_data):
            print("      Upload complete!")
        else:
            print("ERROR: Failed to upload - saving locally")
            self.save_locally(snapshot_data, event_id)
        
        print(f"{'='*50}\n")
    
    def create_event(self) -> str:
        """Create a new event and return event_id."""
        try:
            response = requests.post(
                f"{self.backend_url}/v1/events/start",
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return str(data.get("event_id"))
        except Exception as e:
            print(f"      Error: {e}")
            return None
    
    def upload_base64(self, event_id: str, data: bytes) -> bool:
        """Upload snapshot as base64 to bypass presigned URL issues."""
        try:
            b64_data = base64.b64encode(data).decode('utf-8')
            response = requests.post(
                f"{self.backend_url}/v1/events/{event_id}/upload-base64",
                headers={"Content-Type": "application/json"},
                json={"image_data": b64_data},
                timeout=30
            )
            return response.status_code == 200
        except Exception as e:
            print(f"      Upload error: {e}")
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
        
        # Create detector with our callback
        self._detector = CameraMotionDetector(
            callback=self.on_motion_detected,
            camera_index=0,
            sensitivity=25,
            min_area=5000,
            cooldown_sec=5.0
        )
        
        print("Starting motion detection...")
        print("Press 'q' in preview window to quit (or Ctrl+C)")
        print()
        
        try:
            self._detector.start(show_preview=show_preview)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self._detector.stop()
            print(f"\nTotal events captured: {self.event_count}")


def main():
    show_preview = "--no-preview" not in sys.argv
    client = DoorbellClient()
    client.run(show_preview=show_preview)


if __name__ == "__main__":
    main()
