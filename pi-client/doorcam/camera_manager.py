"""
Camera Manager Module

Handles USB webcam access via OpenCV with live preview support.
Supports auto-detection of camera devices and warmup frames.
"""

import cv2
import time
import glob
import threading
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from . import config


class CameraManager:
    """
    USB Webcam manager using OpenCV.
    
    Features:
    - Auto-detect camera from /dev/v4l/by-id/* (Linux)
    - Fallback to index-based detection (Windows/Mac)
    - Warmup frames before capture
    - Live preview with OpenCV window
    - Thread-safe operations
    """
    
    def __init__(
        self,
        device: str = None,
        width: int = None,
        height: int = None,
        fps: int = None,
        warmup_frames: int = None
    ):
        """
        Initialize camera manager.
        
        Args:
            device: Camera device path or "auto" for auto-detection
            width: Capture width in pixels
            height: Capture height in pixels
            fps: Frames per second
            warmup_frames: Number of frames to discard on startup
        """
        self.device = device or config.CAMERA_DEVICE
        self.width = width or config.CAMERA_WIDTH
        self.height = height or config.CAMERA_HEIGHT
        self.fps = fps or config.CAMERA_FPS
        self.warmup_frames = warmup_frames or config.CAMERA_WARMUP_FRAMES
        
        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        self._preview_running = False
        self._preview_thread: Optional[threading.Thread] = None
        
        # Statistics
        self.frames_captured = 0
        self.snapshots_taken = 0
    
    def _find_camera_device(self) -> str:
        """Auto-detect camera device path."""
        # Try V4L2 by-id paths first (Linux, most stable)
        v4l_paths = glob.glob("/dev/v4l/by-id/*")
        for path in v4l_paths:
            # Skip metadata devices
            if "index1" in path or "index2" in path:
                continue
            print(f"[Camera] Found V4L2 device: {path}")
            return path
        
        # Try standard video devices
        for i in range(5):
            path = f"/dev/video{i}"
            if Path(path).exists():
                print(f"[Camera] Found video device: {path}")
                return path
        
        # Fall back to index (Windows/Mac)
        print("[Camera] Using camera index 0")
        return "0"
    
    def open(self) -> bool:
        """
        Open the camera device.
        
        Returns:
            True if camera opened successfully
        """
        with self._lock:
            if self._cap is not None and self._cap.isOpened():
                print("[Camera] Already open")
                return True
            
            # Determine device to use
            if self.device == "auto":
                device = self._find_camera_device()
            else:
                device = self.device
            
            print(f"[Camera] Opening device: {device}")
            
            # Open with appropriate backend
            if device.isdigit():
                self._cap = cv2.VideoCapture(int(device))
            else:
                # Use V4L2 backend on Linux
                self._cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
            
            if not self._cap.isOpened():
                print("[Camera] Failed to open camera")
                self._cap = None
                return False
            
            # Configure camera
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self._cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Get actual settings
            actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
            
            print(f"[Camera] Opened: {actual_w}x{actual_h} @ {actual_fps:.1f}fps")
            
            # Warmup frames
            print(f"[Camera] Warming up ({self.warmup_frames} frames)...")
            for _ in range(self.warmup_frames):
                self._cap.read()
            print("[Camera] Ready")
            
            return True
    
    def close(self):
        """Close the camera device."""
        self.stop_preview()
        
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
                print("[Camera] Closed")
    
    def read_frame(self) -> Optional[np.ndarray]:
        """
        Read a single frame from the camera.
        
        Returns:
            Frame as numpy array (BGR), or None if failed
        """
        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                return None
            
            ret, frame = self._cap.read()
            if ret:
                self.frames_captured += 1
                return frame
            return None
    
    def capture_snapshot(self, output_path: str = None, quality: int = 95) -> Optional[bytes]:
        """
        Capture a JPEG snapshot.
        
        Args:
            output_path: Optional path to save the image
            quality: JPEG quality (1-100)
            
        Returns:
            JPEG bytes if no output_path, otherwise None on success
        """
        frame = self.read_frame()
        if frame is None:
            print("[Camera] Failed to capture snapshot")
            return None
        
        # Encode as JPEG
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        ret, jpeg_data = cv2.imencode('.jpg', frame, encode_params)
        
        if not ret:
            print("[Camera] Failed to encode JPEG")
            return None
        
        self.snapshots_taken += 1
        
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(jpeg_data.tobytes())
            print(f"[Camera] Snapshot saved: {output_path}")
            return None
        
        return jpeg_data.tobytes()
    
    def start_preview(self, window_name: str = "Camera Preview"):
        """
        Start live preview in an OpenCV window.
        
        Args:
            window_name: Name of the preview window
        """
        if self._preview_running:
            print("[Camera] Preview already running")
            return
        
        if not self.open():
            print("[Camera] Cannot start preview - camera not available")
            return
        
        self._preview_running = True
        self._preview_thread = threading.Thread(
            target=self._preview_loop,
            args=(window_name,),
            daemon=True
        )
        self._preview_thread.start()
        print(f"[Camera] Preview started: '{window_name}'")
    
    def _preview_loop(self, window_name: str):
        """Internal preview loop running in a thread."""
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, self.width, self.height)
        
        fps_counter = 0
        fps_start = time.time()
        display_fps = 0.0
        
        while self._preview_running:
            frame = self.read_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            
            # Calculate FPS
            fps_counter += 1
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                display_fps = fps_counter / elapsed
                fps_counter = 0
                fps_start = time.time()
            
            # Add info overlay
            info_text = f"FPS: {display_fps:.1f} | {frame.shape[1]}x{frame.shape[0]}"
            cv2.putText(
                frame, info_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
            )
            
            # Add instructions
            cv2.putText(
                frame, "Press 'q' to quit, 's' to snapshot", (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
            )
            
            cv2.imshow(window_name, frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self._preview_running = False
            elif key == ord('s'):
                # Take a snapshot
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"snapshot_{timestamp}.jpg"
                self.capture_snapshot(filename)
        
        cv2.destroyWindow(window_name)
        print("[Camera] Preview stopped")
    
    def stop_preview(self):
        """Stop the live preview."""
        if not self._preview_running:
            return
        
        self._preview_running = False
        if self._preview_thread is not None:
            self._preview_thread.join(timeout=2.0)
            self._preview_thread = None
    
    def run_preview_blocking(self, window_name: str = "Camera Preview"):
        """
        Run live preview in the main thread (blocking).
        
        This is useful for simple testing scripts.
        """
        if not self.open():
            print("[Camera] Cannot start preview - camera not available")
            return
        
        print(f"[Camera] Starting blocking preview: '{window_name}'")
        print("Press 'q' to quit, 's' to take snapshot")
        
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, self.width, self.height)
        
        fps_counter = 0
        fps_start = time.time()
        display_fps = 0.0
        
        try:
            while True:
                frame = self.read_frame()
                if frame is None:
                    print("[Camera] Failed to read frame, retrying...")
                    time.sleep(0.5)
                    continue
                
                # Calculate FPS
                fps_counter += 1
                elapsed = time.time() - fps_start
                if elapsed >= 1.0:
                    display_fps = fps_counter / elapsed
                    fps_counter = 0
                    fps_start = time.time()
                
                # Add info overlay
                info_text = f"FPS: {display_fps:.1f} | {frame.shape[1]}x{frame.shape[0]}"
                cv2.putText(
                    frame, info_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
                )
                
                cv2.putText(
                    frame, "Press 'q' to quit, 's' to snapshot", (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
                )
                
                cv2.imshow(window_name, frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"snapshot_{timestamp}.jpg"
                    self.capture_snapshot(filename)
        
        except KeyboardInterrupt:
            print("\n[Camera] Interrupted")
        finally:
            cv2.destroyAllWindows()
            self.close()
    
    def get_stats(self) -> dict:
        """Get camera statistics."""
        return {
            "frames_captured": self.frames_captured,
            "snapshots_taken": self.snapshots_taken,
            "is_open": self._cap is not None and self._cap.isOpened() if self._cap else False,
            "preview_running": self._preview_running,
            "resolution": f"{self.width}x{self.height}",
            "fps": self.fps
        }


# Simple test script
if __name__ == "__main__":
    import sys
    
    print("=" * 50)
    print("Camera Manager Test")
    print("=" * 50)
    print()
    
    print("[Test] Creating camera manager...")
    camera = CameraManager()
    
    print(f"[Test] Device: {camera.device}")
    print(f"[Test] Resolution: {camera.width}x{camera.height}")
    print()
    
    print("[Test] Opening camera...")
    if not camera.open():
        print("[Test] ERROR: Failed to open camera!")
        print("[Test] Check that your webcam is connected and not in use by another app.")
        sys.exit(1)
    
    print("[Test] Starting preview window...")
    print("[Test] Press 'q' in the window to quit, 's' to snapshot")
    print()
    
    camera.run_preview_blocking()
    
    print()
    print("[Test] Final stats:", camera.get_stats())
