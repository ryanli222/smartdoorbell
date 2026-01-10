"""
Combined Test: Motion-Triggered Camera Capture

This script demonstrates the motion sensor and camera working together.
When motion is detected, it captures a snapshot.
"""

import sys
import time
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from doorcam.motion_sensor import MotionSensor
from doorcam.camera_manager import CameraManager


def main():
    print("=" * 60)
    print("Motion-Triggered Camera Test")
    print("=" * 60)
    print()
    
    # Initialize camera
    camera = CameraManager()
    if not camera.open():
        print("ERROR: Could not open camera!")
        return
    
    # Motion callback - captures snapshot
    def on_motion():
        print("\n*** MOTION DETECTED - Capturing snapshot... ***")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"motion_capture_{timestamp}.jpg"
        camera.capture_snapshot(filename)
        print(f"*** Saved: {filename} ***\n")
    
    # Initialize motion sensor (mock mode for testing)
    sensor = MotionSensor(callback=on_motion, mock_mode=True)
    sensor.start()
    
    print("System ready!")
    print()
    print("Commands:")
    print("  Press ENTER - Simulate motion (captures snapshot)")
    print("  Type 'preview' - Open camera preview window")
    print("  Type 'stats' - Show statistics")
    print("  Type 'quit' - Exit")
    print()
    
    try:
        while True:
            cmd = input("> ").strip().lower()
            
            if cmd == "quit" or cmd == "q":
                break
            elif cmd == "preview" or cmd == "p":
                print("Opening preview (press 'q' in window to close)...")
                camera.run_preview_blocking()
                # Reopen camera after preview closes
                camera.open()
            elif cmd == "stats":
                print("\nMotion Sensor:", sensor.get_stats())
                print("Camera:", camera.get_stats())
                print()
            else:
                # Simulate motion on Enter
                sensor.simulate_motion()
    
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        print("\nShutting down...")
        sensor.stop()
        camera.close()
        print("Done!")


if __name__ == "__main__":
    main()
