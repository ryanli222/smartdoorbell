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
    display_duration: float = 10.0,
    audio_file: str = None
):
    """
    Run motion-triggered camera display.
    
    Shows clean camera feed when motion is detected.
    
    Args:
        sensitivity: Motion detection sensitivity (lower = more sensitive)
        min_area: Minimum motion area to trigger
        display_duration: How long to show camera after motion
        audio_file: Path to audio file to play on motion
    """
    print("=" * 60)
    print("Motion-Triggered Camera Display")
    print("=" * 60)
    print()
    
    # Create display
    display = LiveCameraDisplay(
        display_duration_sec=display_duration,
        audio_file=audio_file or config.ALERT_AUDIO_FILE
    )
    
    # Create motion detector with trigger callback
    def on_motion():
        print("[Motion] Detected! Showing camera...")
        display.trigger()
    
    detector = CameraMotionDetector(
        callback=on_motion,
        sensitivity=sensitivity,
        min_area=min_area,
        cooldown_sec=2.0
    )
    
    print(f"[Setup] Audio file: {audio_file or config.ALERT_AUDIO_FILE or 'None'}")
    print(f"[Setup] Display duration: {display_duration}s")
    print(f"[Setup] Sensitivity: {sensitivity}")
    print()
    
    # Start motion detection in background
    detector.start(show_preview=False)
    
    print("[Ready] Watching for motion...")
    print("[Ready] Press 'q' in popup window to quit")
    print()
    
    try:
        display.run_display_loop()
    finally:
        detector.stop()
        print("[Done] Stopped")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Motion-triggered camera display")
    parser.add_argument("--audio", type=str, help="Path to audio file to play on motion")
    parser.add_argument("--duration", type=float, default=10.0, help="Display duration in seconds")
    parser.add_argument("--sensitivity", type=float, default=25.0, help="Motion sensitivity (lower = more)")
    parser.add_argument("--min-area", type=int, default=5000, help="Minimum motion area")
    
    args = parser.parse_args()
    
    run_motion_triggered_display(
        sensitivity=args.sensitivity,
        min_area=args.min_area,
        display_duration=args.duration,
        audio_file=args.audio
    )
