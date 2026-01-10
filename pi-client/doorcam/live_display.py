"""
Motion-Triggered Camera Display

Shows a clean "LIVE" camera feed when motion is detected.
Plays an optional audio alert and pops up a minimal preview window.
"""

import cv2
import time
import threading
from pathlib import Path
from . import config
from .camera_manager import CameraManager
from .camera_motion import CameraMotionDetector
from .audio import play_audio
from .audio_relay import AudioRelay


class LiveCameraDisplay:
    """
    Displays a clean live camera feed when motion is detected.
    
    Features:
    - Minimal "LIVE" indicator in corner
    - Optional audio alert on popup
    - Auto-hides after configurable timeout
    """
    
    def __init__(
        self,
        camera: CameraManager = None,
        display_duration_sec: float = 10.0,
        audio_file: str = None,
        window_name: str = "Doorbell Camera"
    ):
        """
        Initialize live camera display.
        
        Args:
            camera: CameraManager instance (created if not provided)
            display_duration_sec: How long to show the preview
            audio_file: Path to audio file to play (uses config if not provided)
            window_name: Name of the display window
        """
        self.camera = camera or CameraManager()
        self.display_duration_sec = display_duration_sec
        self.audio_file = audio_file or config.ALERT_AUDIO_FILE
        self.window_name = window_name
        
        self._showing = False
        self._show_until = 0
        self._lock = threading.Lock()
    
    def _draw_live_indicator(self, frame):
        """Draw a minimal LIVE indicator in the corner."""
        height, width = frame.shape[:2]
        
        # Red circle (recording dot)
        circle_x = width - 80
        circle_y = 30
        cv2.circle(frame, (circle_x, circle_y), 8, (0, 0, 255), -1)
        
        # "LIVE" text
        cv2.putText(
            frame, "LIVE",
            (circle_x + 15, circle_y + 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6, (255, 255, 255), 2
        )
        
        return frame
    
    def trigger(self):
        """Trigger the camera display (called on motion detection)."""
        with self._lock:
            self._show_until = time.time() + self.display_duration_sec
            
            if not self._showing:
                self._showing = True
                # Play audio alert
                if self.audio_file:
                    play_audio(self.audio_file)
    
    def run_display_loop(self):
        """
        Run the display loop (blocking).
        
        Call trigger() from another thread to show the camera.
        Press 'q' to quit.
        """
        if not self.camera.open():
            print("[LiveDisplay] Failed to open camera")
            return
        
        print(f"[LiveDisplay] Ready. Window: '{self.window_name}'")
        print("[LiveDisplay] Press 'q' to quit")
        
        window_created = False
        
        try:
            while True:
                current_time = time.time()
                
                with self._lock:
                    should_show = current_time < self._show_until
                
                if should_show:
                    # Create window if not exists
                    if not window_created:
                        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
                        cv2.resizeWindow(self.window_name, self.camera.width, self.camera.height)
                        window_created = True
                    
                    # Read and display frame
                    frame = self.camera.read_frame()
                    if frame is not None:
                        # Add only the LIVE indicator
                        frame = self._draw_live_indicator(frame)
                        cv2.imshow(self.window_name, frame)
                    
                    # Check for 'q' key
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                else:
                    # Hide window when not showing
                    if window_created:
                        cv2.destroyWindow(self.window_name)
                        window_created = False
                        with self._lock:
                            self._showing = False
                    
                    # Sleep to reduce CPU usage when not displaying
                    time.sleep(0.1)
                    
                    # Still check for quit
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
        
        finally:
            cv2.destroyAllWindows()
            self.camera.close()
    
    def show_now(self):
        """Immediately trigger display for the configured duration."""
        self.trigger()


def run_motion_triggered_display(
    sensitivity: float = 25.0,
    min_area: int = 5000,
    display_duration: float = 15.0,
    snapshot_delay: float = 3.0,
    audio_file: str = None,
    backend_url: str = None
):
    """
    Run motion-triggered camera display with snapshot upload.
    
    Shows clean camera feed when motion is detected.
    Uploads a snapshot to the backend 3 seconds after motion.
    Window closes after exactly 15 seconds (hard timer).
    """
    import os
    import base64
    import signal
    
    # Handle Ctrl+C properly
    running = [True]  # Use list to allow modification in signal handler
    def signal_handler(sig, frame):
        print("\n[Ctrl+C] Shutting down...")
        running[0] = False
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        import requests
    except ImportError:
        print("[Warning] requests not installed - snapshot upload disabled")
        requests = None
    
    backend = backend_url or os.getenv("BACKEND_URL", "http://localhost:8000")
    
    print("=" * 60)
    print("Motion-Triggered Camera Display")
    print("=" * 60)
    print()
    
    # Open camera ONCE
    print("[Setup] Opening camera...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("[ERROR] Could not open camera!")
            return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print(f"[Setup] Camera opened: {int(cap.get(3))}x{int(cap.get(4))}")
    
    # State variables
    motion_start_time = 0  # When motion started (for hard 15s timer)
    snapshot_at = 0
    snapshot_taken = False
    in_motion_session = False  # Track if we're in a motion session
    pause_until = 0  # When to resume detection
    prev_frame = None
    motion_count = 0
    audio = audio_file or config.ALERT_AUDIO_FILE
    
    # Audio relay for live mic passthrough
    audio_relay = AudioRelay()
    
    print(f"[Setup] Backend: {backend}")
    print(f"[Setup] Display duration: {display_duration}s (hard close)")
    print(f"[Setup] Snapshot at: {snapshot_delay}s after motion")
    print(f"[Setup] Audio file: {audio or 'None'}")
    print()
    print("[Ready] Watching for motion...")
    print("[Keys] 'q' = quit, 'f' = pause for 1 minute")
    print()
    
    window_open = False
    
    def upload_snapshot(frame_data):
        """Upload snapshot to backend."""
        try:
            # Encode frame as JPEG
            _, jpeg = cv2.imencode('.jpg', frame_data, [cv2.IMWRITE_JPEG_QUALITY, 85])
            b64_data = base64.b64encode(jpeg.tobytes()).decode('utf-8')
            
            # Headers to bypass ngrok warning page
            headers = {
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"
            }
            
            # Create event
            resp = requests.post(
                f"{backend}/v1/events/start",
                headers=headers,
                timeout=10
            )
            if resp.status_code != 200:
                print(f"[Upload] Failed to create event: {resp.status_code} - {resp.text[:100]}")
                return
            
            event_id = resp.json().get("event_id")
            print(f"[Upload] Event created: {event_id}")
            
            # Upload base64
            resp = requests.post(
                f"{backend}/v1/events/{event_id}/upload-base64",
                json={"image_data": b64_data},
                headers=headers,
                timeout=30
            )
            if resp.status_code == 200:
                print(f"[Upload] Snapshot uploaded successfully!")
            else:
                print(f"[Upload] Upload failed: {resp.status_code}")
        except Exception as e:
            print(f"[Upload] Error: {e}")
    
    try:
        while running[0]:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            current_time = time.time()
            
            # Check if paused
            is_paused = current_time < pause_until
            if is_paused:
                pause_remaining = int(pause_until - current_time)
                # Show pause status
                h, w = frame.shape[:2]
                cv2.putText(frame, f"PAUSED ({pause_remaining}s)", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                cv2.imshow("Doorbell Camera", frame)
                
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('f'):
                    # Cancel pause
                    pause_until = 0
                    print("[Pause] Cancelled - detection resumed")
                continue
            
            # Calculate time since motion started
            time_since_motion = current_time - motion_start_time if motion_start_time > 0 else 0
            session_should_end = in_motion_session and time_since_motion >= display_duration
            
            # Motion detection (only when not in a session)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            
            if prev_frame is not None and not in_motion_session:
                diff = cv2.absdiff(prev_frame, gray)
                thresh = cv2.threshold(diff, sensitivity, 255, cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    if cv2.contourArea(contour) > min_area:
                        motion_count += 1
                        motion_start_time = current_time
                        snapshot_at = current_time + snapshot_delay
                        snapshot_taken = False
                        in_motion_session = True
                        print(f"[Motion #{motion_count}] Detected! Window opens for {display_duration}s")
                        if audio:
                            play_audio(audio)
                        # Start audio relay after 5s delay (in background so camera doesn't freeze)
                        def start_relay_delayed():
                            time.sleep(5.0)
                            audio_relay.start()
                        threading.Thread(target=start_relay_delayed, daemon=True).start()
                        break
            
            prev_frame = gray
            
            # Snapshot capture (3 seconds after motion)
            if in_motion_session and not snapshot_taken and current_time >= snapshot_at:
                snapshot_taken = True
                print("[Capture] Taking snapshot...")
                threading.Thread(target=upload_snapshot, args=(frame.copy(),), daemon=True).start()
            
            # Display logic
            if in_motion_session and not session_should_end:
                if not window_open:
                    cv2.namedWindow("Doorbell Camera", cv2.WND_PROP_FULLSCREEN)
                    cv2.setWindowProperty("Doorbell Camera", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                    window_open = True
                
                # Draw LIVE indicator
                h, w = frame.shape[:2]
                cv2.circle(frame, (w - 80, 30), 8, (0, 0, 255), -1)
                cv2.putText(frame, "LIVE", (w - 65, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # Show time remaining
                remaining = int(display_duration - time_since_motion)
                cv2.putText(frame, f"{remaining}s", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                cv2.imshow("Doorbell Camera", frame)
            elif session_should_end:
                # Hard close after 15 seconds
                if window_open:
                    cv2.destroyWindow("Doorbell Camera")
                    window_open = False
                    print(f"[Session] Window closed after {display_duration}s")
                # Stop audio relay
                audio_relay.stop()
                in_motion_session = False
                motion_start_time = 0
            
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('f'):
                pause_until = current_time + 60
                print("[Pause] Detection paused for 60 seconds (press 'f' again to cancel)")
                if not window_open:
                    cv2.namedWindow("Doorbell Camera", cv2.WINDOW_NORMAL)
                    window_open = True
    
    finally:
        audio_relay.stop()  # Stop audio relay if running
        cap.release()
        cv2.destroyAllWindows()
        print(f"\n[Done] Total motion events: {motion_count}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Motion-triggered camera display")
    parser.add_argument("--audio", type=str, help="Path to audio file to play on motion")
    parser.add_argument("--duration", type=float, default=15.0, help="Display duration in seconds")
    parser.add_argument("--snapshot-delay", type=float, default=3.0, help="Seconds after motion to capture snapshot")
    parser.add_argument("--sensitivity", type=float, default=25.0, help="Motion sensitivity (lower = more)")
    parser.add_argument("--min-area", type=int, default=5000, help="Minimum motion area")
    parser.add_argument("--backend", type=str, help="Backend URL for uploading snapshots")
    
    args = parser.parse_args()
    
    run_motion_triggered_display(
        sensitivity=args.sensitivity,
        min_area=args.min_area,
        display_duration=args.duration,
        snapshot_delay=args.snapshot_delay,
        audio_file=args.audio,
        backend_url=args.backend
    )
