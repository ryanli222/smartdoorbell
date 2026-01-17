"""
Gesture Detector Module (Unified version)

Automatically uses MediaPipe on laptop/desktop, falls back to OpenCV on Pi.
Currently supports: Peace sign (✌️)
"""

import cv2
import numpy as np
import time
from typing import Tuple, Optional

# Try to import MediaPipe (works on laptop, not on Pi)
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
    print("[GestureDetector] MediaPipe available - using ML-based detection")
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("[GestureDetector] MediaPipe not available - using OpenCV fallback")


class GestureDetector:
    """
    Detects hand gestures.
    
    Uses MediaPipe (accurate) if available, otherwise falls back to
    OpenCV skin detection (works on Pi).
    
    Currently supports:
    - Peace sign (index + middle fingers extended, others folded)
    """
    
    def __init__(
        self,
        cooldown_sec: float = 5.0,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
        min_hand_area: int = 5000
    ):
        """
        Initialize gesture detector.
        
        Args:
            cooldown_sec: Seconds to wait before triggering same gesture again
            min_detection_confidence: MediaPipe detection confidence (if available)
            min_tracking_confidence: MediaPipe tracking confidence (if available)
            min_hand_area: Minimum contour area for OpenCV fallback
        """
        self.cooldown_sec = cooldown_sec
        self.min_hand_area = min_hand_area
        self._last_peace_sign_time = 0
        self._use_mediapipe = MEDIAPIPE_AVAILABLE
        
        # MediaPipe setup
        self._hands = None
        self._mp_hands = None
        self._mp_draw = None
        
        if self._use_mediapipe:
            self._mp_hands = mp.solutions.hands
            self._hands = self._mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence
            )
            self._mp_draw = mp.solutions.drawing_utils
        
        # OpenCV fallback: skin color range in HSV
        self.lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        self.upper_skin = np.array([20, 255, 255], dtype=np.uint8)
    
    # ==================== MediaPipe Methods ====================
    
    def _is_finger_extended(self, landmarks, tip_idx: int, pip_idx: int) -> bool:
        """Check if finger is extended (MediaPipe)."""
        return landmarks[tip_idx].y < landmarks[pip_idx].y
    
    def _is_finger_folded(self, landmarks, tip_idx: int, mcp_idx: int) -> bool:
        """Check if finger is folded (MediaPipe)."""
        return landmarks[tip_idx].y > landmarks[mcp_idx].y
    
    def _detect_mediapipe(self, frame) -> Tuple[bool, Optional[object]]:
        """Detect peace sign using MediaPipe."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb_frame)
        
        if not results.multi_hand_landmarks:
            return False, None
        
        for hand_landmarks in results.multi_hand_landmarks:
            lm = hand_landmarks.landmark
            
            # Peace sign: Index(8,6) and Middle(12,10) extended, Ring(16,13) and Pinky(20,17) folded
            index_extended = self._is_finger_extended(lm, 8, 6)
            middle_extended = self._is_finger_extended(lm, 12, 10)
            ring_folded = self._is_finger_folded(lm, 16, 13)
            pinky_folded = self._is_finger_folded(lm, 20, 17)
            
            if index_extended and middle_extended and ring_folded and pinky_folded:
                return True, hand_landmarks
        
        return False, None
    
    # ==================== OpenCV Fallback Methods ====================
    
    def _count_fingers_opencv(self, contour) -> int:
        """Count fingers using convex hull defects (OpenCV fallback)."""
        hull = cv2.convexHull(contour, returnPoints=False)
        
        if len(hull) < 3:
            return 0
        
        try:
            defects = cv2.convexityDefects(contour, hull)
        except:
            return 0
        
        if defects is None:
            return 0
        
        finger_count = 0
        for i in range(defects.shape[0]):
            s, e, f, d = defects[i, 0]
            start = tuple(contour[s][0])
            end = tuple(contour[e][0])
            far = tuple(contour[f][0])
            
            a = np.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
            b = np.sqrt((far[0] - start[0])**2 + (far[1] - start[1])**2)
            c = np.sqrt((end[0] - far[0])**2 + (end[1] - far[1])**2)
            
            if b * c == 0:
                continue
            angle = np.arccos((b**2 + c**2 - a**2) / (2 * b * c))
            
            if angle <= np.pi / 2:
                finger_count += 1
        
        return finger_count + 1
    
    def _detect_opencv(self, frame) -> Tuple[bool, Optional[np.ndarray]]:
        """Detect peace sign using OpenCV skin detection."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_skin, self.upper_skin)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        mask = cv2.erode(mask, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=2)
        mask = cv2.GaussianBlur(mask, (3, 3), 0)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return False, mask
        
        max_contour = max(contours, key=cv2.contourArea)
        if cv2.contourArea(max_contour) < self.min_hand_area:
            return False, mask
        
        finger_count = self._count_fingers_opencv(max_contour)
        
        if finger_count == 2:
            return True, mask
        
        return False, mask
    
    # ==================== Public API ====================
    
    def detect_peace_sign(self, frame) -> Tuple[bool, Optional[object]]:
        """
        Detect peace sign gesture in the frame.
        
        Returns:
            Tuple of (detected: bool, landmarks/mask for drawing)
        """
        current_time = time.time()
        if current_time - self._last_peace_sign_time < self.cooldown_sec:
            return False, None
        
        if self._use_mediapipe:
            detected, data = self._detect_mediapipe(frame)
        else:
            detected, data = self._detect_opencv(frame)
        
        if detected:
            self._last_peace_sign_time = current_time
        
        return detected, data
    
    def draw_landmarks(self, frame, data):
        """Draw detection visualization on the frame."""
        if data is None:
            return frame
        
        if self._use_mediapipe:
            self._mp_draw.draw_landmarks(frame, data, self._mp_hands.HAND_CONNECTIONS)
        else:
            # OpenCV: draw contours
            contours, _ = cv2.findContours(data, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                max_contour = max(contours, key=cv2.contourArea)
                if cv2.contourArea(max_contour) > self.min_hand_area:
                    cv2.drawContours(frame, [max_contour], -1, (0, 255, 0), 2)
                    hull = cv2.convexHull(max_contour)
                    cv2.drawContours(frame, [hull], -1, (255, 0, 0), 2)
        
        return frame
    
    def close(self):
        """Release resources."""
        if self._hands:
            self._hands.close()
            self._hands = None


# ==================== Test Script ====================

if __name__ == "__main__":
    print("=" * 50)
    print("Gesture Detector Test")
    print("=" * 50)
    print(f"Mode: {'MediaPipe (accurate)' if MEDIAPIPE_AVAILABLE else 'OpenCV (fallback)'}")
    print()
    
    detector = GestureDetector(cooldown_sec=2.0)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Could not open camera!")
        exit(1)
    
    print("Camera opened. Show a peace sign ✌️ to test!")
    print("Press 'q' to quit.")
    print()
    
    peace_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame = cv2.flip(frame, 1)
            detected, data = detector.detect_peace_sign(frame)
            
            if detected:
                peace_count += 1
                print(f"[{peace_count}] Peace sign detected! ✌️")
            
            if data is not None:
                detector.draw_landmarks(frame, data)
            
            # Status display
            mode = "MediaPipe" if MEDIAPIPE_AVAILABLE else "OpenCV"
            status = "PEACE SIGN!" if detected else f"Watching... ({mode})"
            color = (0, 255, 0) if detected else (255, 255, 255)
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            cv2.imshow("Gesture Detector Test", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        detector.close()
        cap.release()
        cv2.destroyAllWindows()
        print(f"\nTotal peace signs detected: {peace_count}")
