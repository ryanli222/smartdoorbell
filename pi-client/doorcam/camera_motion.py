"""
Camera Motion Detection Module

Detects motion by comparing consecutive camera frames.
No external sensors needed - uses the existing USB webcam.
"""

import cv2
import time
import numpy as np
import threading
from typing import Callable, Optional
from . import config


class CameraMotionDetector:
    """
    Detects motion using camera frame differencing.
    
    Compares consecutive frames and triggers callback when
    significant pixel changes are detected.
    """
    
    def __init__(
        self,
        callback: Callable[[], None],
        camera_index: int = 0,
        sensitivity: float = 25.0,
        min_area: int = 5000,
        cooldown_sec: float = 3.0,
        blur_size: int = 21
    ):
        """
        Initialize motion detector.
        
        Args:
            callback: Function to call when motion detected
            camera_index: Camera device index (0 = first camera)
            sensitivity: Motion threshold (lower = more sensitive)
            min_area: Minimum contour area to trigger (pixels)
            cooldown_sec: Minimum time between triggers
            blur_size: Gaussian blur kernel size (must be odd)
        """
        self.callback = callback
        self.camera_index = camera_index
        self.sensitivity = sensitivity
        self.min_area = min_area
        self.cooldown_sec = cooldown_sec
        self.blur_size = blur_size
        
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_trigger_time = 0
        self._prev_frame = None
        
        # Stats
        self.trigger_count = 0
        self.frames_processed = 0
        self.last_motion_area = 0
    
    def _open_camera(self) -> bool:
        """Open the camera."""
        self._cap = cv2.VideoCapture(self.camera_index)
        if not self._cap.isOpened():
            print(f"[MotionDetect] Failed to open camera {self.camera_index}")
            return False
        
        # Set resolution for faster processing
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print(f"[MotionDetect] Camera {self.camera_index} opened")
        return True
    
    def _process_frame(self, frame) -> tuple:
        """
        Process frame for motion detection.
        
        Returns:
            (motion_detected: bool, motion_area: int, diff_frame)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (self.blur_size, self.blur_size), 0)
        
        if self._prev_frame is None:
            self._prev_frame = gray
            return False, 0, None
        
        # Calculate frame difference
        frame_diff = cv2.absdiff(self._prev_frame, gray)
        self._prev_frame = gray
        
        # Threshold the difference
        thresh = cv2.threshold(frame_diff, self.sensitivity, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Check for significant motion
        motion_detected = False
        total_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_area:
                motion_detected = True
                total_area += area
        
        return motion_detected, total_area, thresh
    
    def _detection_loop(self, show_preview: bool = False):
        """Main detection loop."""
        print("[MotionDetect] Detection loop started")
        
        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            self.frames_processed += 1
            motion_detected, motion_area, thresh = self._process_frame(frame)
            self.last_motion_area = motion_area
            
            if motion_detected:
                current_time = time.time()
                time_since_last = current_time - self._last_trigger_time
                
                if time_since_last >= self.cooldown_sec:
                    self._last_trigger_time = current_time
                    self.trigger_count += 1
                    print(f"[MotionDetect] MOTION! Area: {motion_area} (trigger #{self.trigger_count})")
                    
                    try:
                        self.callback()
                    except Exception as e:
                        print(f"[MotionDetect] Callback error: {e}")
            
            if show_preview and thresh is not None:
                # Draw motion status
                status = "MOTION!" if motion_detected else "Watching..."
                color = (0, 0, 255) if motion_detected else (0, 255, 0)
                cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                cv2.putText(frame, f"Area: {motion_area}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                
                cv2.imshow("Motion Detection", frame)
                cv2.imshow("Threshold", thresh)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self._running = False
            
            time.sleep(0.03)  # ~30 FPS
    
    def start(self, show_preview: bool = False):
        """Start motion detection."""
        if self._running:
            print("[MotionDetect] Already running")
            return
        
        if not self._open_camera():
            return
        
        self._running = True
        self._prev_frame = None
        
        if show_preview:
            # Run in main thread for preview
            self._detection_loop(show_preview=True)
            self.stop()
        else:
            # Run in background thread
            self._thread = threading.Thread(target=self._detection_loop, daemon=True)
            self._thread.start()
            print("[MotionDetect] Running in background")
    
    def stop(self):
        """Stop motion detection."""
        if not self._running:
            return
        
        print("[MotionDetect] Stopping...")
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        
        if self._cap:
            self._cap.release()
            self._cap = None
        
        cv2.destroyAllWindows()
        print("[MotionDetect] Stopped")
    
    def get_stats(self) -> dict:
        """Get detection statistics."""
        return {
            "trigger_count": self.trigger_count,
            "frames_processed": self.frames_processed,
            "last_motion_area": self.last_motion_area,
            "running": self._running,
            "sensitivity": self.sensitivity,
            "min_area": self.min_area
        }


# Test script
if __name__ == "__main__":
    print("=" * 50)
    print("Camera Motion Detection Test")
    print("=" * 50)
    print()
    print("Press 'q' in the preview window to quit.")
    print()
    
    def on_motion():
        print("\n*** MOTION DETECTED! ***\n")
    
    detector = CameraMotionDetector(
        callback=on_motion,
        camera_index=0,
        sensitivity=25,
        min_area=5000,
        cooldown_sec=2.0
    )
    
    try:
        detector.start(show_preview=True)
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        detector.stop()
        print("\nFinal stats:", detector.get_stats())
