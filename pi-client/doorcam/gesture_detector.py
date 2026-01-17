"""
Gesture Detector Module (OpenCV-only version)

Detects hand gestures using skin color detection and contour analysis.
Works on Raspberry Pi without MediaPipe.

Currently supports: Peace sign (✌️) - detected as 2 extended fingers
"""

import cv2
import numpy as np
import time
from typing import Tuple, Optional


class GestureDetector:
    """
    Detects hand gestures using OpenCV skin color detection.
    
    This is a simpler approach that works on Raspberry Pi 5
    without requiring MediaPipe.
    
    Currently supports:
    - Peace sign (2 extended fingers detected)
    """
    
    def __init__(
        self,
        cooldown_sec: float = 5.0,
        min_hand_area: int = 5000
    ):
        """
        Initialize gesture detector.
        
        Args:
            cooldown_sec: Seconds to wait before triggering same gesture again
            min_hand_area: Minimum contour area to consider as a hand
        """
        self.cooldown_sec = cooldown_sec
        self.min_hand_area = min_hand_area
        self._last_peace_sign_time = 0
        
        # Skin color range in HSV (adjust if needed for different skin tones)
        self.lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        self.upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        
        print("[GestureDetector] Initialized with OpenCV skin detection")
    
    def _count_fingers(self, contour, frame_shape) -> Tuple[int, list]:
        """
        Count extended fingers using convex hull defects.
        
        Returns:
            Tuple of (finger_count, defect_points for drawing)
        """
        # Get convex hull
        hull = cv2.convexHull(contour, returnPoints=False)
        
        if len(hull) < 3:
            return 0, []
        
        try:
            defects = cv2.convexityDefects(contour, hull)
        except:
            return 0, []
        
        if defects is None:
            return 0, []
        
        finger_count = 0
        defect_points = []
        
        for i in range(defects.shape[0]):
            s, e, f, d = defects[i, 0]
            start = tuple(contour[s][0])
            end = tuple(contour[e][0])
            far = tuple(contour[f][0])
            
            # Calculate the angle between fingers
            a = np.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
            b = np.sqrt((far[0] - start[0])**2 + (far[1] - start[1])**2)
            c = np.sqrt((end[0] - far[0])**2 + (end[1] - far[1])**2)
            
            # Cosine rule to find angle
            if b * c == 0:
                continue
            angle = np.arccos((b**2 + c**2 - a**2) / (2 * b * c))
            
            # If angle is less than 90 degrees, it's a finger gap
            if angle <= np.pi / 2:
                finger_count += 1
                defect_points.append(far)
        
        # finger_count is the number of gaps, so fingers = gaps + 1
        return finger_count + 1, defect_points
    
    def detect_peace_sign(self, frame) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Detect peace sign gesture in the frame.
        
        Args:
            frame: BGR image from OpenCV
            
        Returns:
            Tuple of (detected: bool, mask for visualization or None)
        """
        # Check cooldown
        current_time = time.time()
        if current_time - self._last_peace_sign_time < self.cooldown_sec:
            return False, None
        
        # Convert to HSV for skin detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Create skin mask
        mask = cv2.inRange(hsv, self.lower_skin, self.upper_skin)
        
        # Clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        mask = cv2.erode(mask, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=2)
        mask = cv2.GaussianBlur(mask, (3, 3), 0)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return False, mask
        
        # Find the largest contour (presumably the hand)
        max_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(max_contour)
        
        if area < self.min_hand_area:
            return False, mask
        
        # Count fingers
        finger_count, _ = self._count_fingers(max_contour, frame.shape)
        
        # Peace sign = 2 fingers extended
        if finger_count == 2:
            self._last_peace_sign_time = current_time
            return True, mask
        
        return False, mask
    
    def draw_landmarks(self, frame, mask):
        """Draw detection visualization on the frame."""
        if mask is not None:
            # Find contours on the mask
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                max_contour = max(contours, key=cv2.contourArea)
                if cv2.contourArea(max_contour) > self.min_hand_area:
                    # Draw the hand contour
                    cv2.drawContours(frame, [max_contour], -1, (0, 255, 0), 2)
                    # Draw convex hull
                    hull = cv2.convexHull(max_contour)
                    cv2.drawContours(frame, [hull], -1, (255, 0, 0), 2)
        return frame
    
    def close(self):
        """Release resources (no-op for OpenCV version)."""
        pass


# Test script
if __name__ == "__main__":
    print("=" * 50)
    print("Gesture Detector Test (OpenCV version)")
    print("=" * 50)
    print()
    print("This uses skin color detection - works best with:")
    print("- Good lighting")
    print("- Plain background")
    print("- Hand clearly visible")
    print()
    
    detector = GestureDetector(cooldown_sec=2.0)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Could not open camera!")
        exit(1)
    
    print("Camera opened. Show a peace sign ✌️ (2 fingers) to test!")
    print("Press 'q' to quit, 'd' to toggle debug view.")
    print()
    
    peace_count = 0
    show_debug = False
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Flip for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Detect peace sign
            detected, mask = detector.detect_peace_sign(frame)
            
            if detected:
                peace_count += 1
                print(f"[{peace_count}] Peace sign detected! ✌️")
            
            # Draw visualization
            detector.draw_landmarks(frame, mask)
            
            # Show status
            status = "PEACE SIGN!" if detected else "Show 2 fingers..."
            color = (0, 255, 0) if detected else (255, 255, 255)
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            # Show main view
            cv2.imshow("Gesture Detector Test", frame)
            
            # Show debug mask if enabled
            if show_debug and mask is not None:
                cv2.imshow("Skin Mask (Debug)", mask)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                show_debug = not show_debug
                if not show_debug:
                    cv2.destroyWindow("Skin Mask (Debug)")
    
    finally:
        detector.close()
        cap.release()
        cv2.destroyAllWindows()
        print(f"\nTotal peace signs detected: {peace_count}")
