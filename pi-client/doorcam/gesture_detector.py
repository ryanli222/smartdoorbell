"""
Gesture Detector Module

Detects hand gestures using MediaPipe.
Currently supports: Peace sign (✌️)
"""

import time
from typing import Optional, Tuple

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("[GestureDetector] MediaPipe not installed - gesture detection disabled")


class GestureDetector:
    """
    Detects hand gestures using MediaPipe Hands.
    
    Currently supports:
    - Peace sign (index + middle fingers extended, others folded)
    """
    
    def __init__(
        self,
        cooldown_sec: float = 5.0,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5
    ):
        """
        Initialize gesture detector.
        
        Args:
            cooldown_sec: Seconds to wait before triggering same gesture again
            min_detection_confidence: MediaPipe detection confidence threshold
            min_tracking_confidence: MediaPipe tracking confidence threshold
        """
        self.cooldown_sec = cooldown_sec
        self._last_peace_sign_time = 0
        self._hands = None
        
        if MEDIAPIPE_AVAILABLE:
            self._mp_hands = mp.solutions.hands
            self._hands = self._mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence
            )
            self._mp_draw = mp.solutions.drawing_utils
            print("[GestureDetector] Initialized with MediaPipe Hands")
    
    def _is_finger_extended(self, landmarks, finger_tip_idx: int, finger_pip_idx: int) -> bool:
        """Check if a finger is extended based on tip vs PIP joint position."""
        tip = landmarks[finger_tip_idx]
        pip = landmarks[finger_pip_idx]
        # Finger is extended if tip is above (lower y value) the PIP joint
        return tip.y < pip.y
    
    def _is_finger_folded(self, landmarks, finger_tip_idx: int, finger_mcp_idx: int) -> bool:
        """Check if a finger is folded (curled down)."""
        tip = landmarks[finger_tip_idx]
        mcp = landmarks[finger_mcp_idx]
        # Finger is folded if tip is below (higher y value) the MCP joint
        return tip.y > mcp.y
    
    def detect_peace_sign(self, frame) -> Tuple[bool, Optional[object]]:
        """
        Detect peace sign gesture in the frame.
        
        Args:
            frame: BGR image from OpenCV
            
        Returns:
            Tuple of (detected: bool, hand_landmarks for drawing or None)
        """
        if not MEDIAPIPE_AVAILABLE or self._hands is None:
            return False, None
        
        # Check cooldown
        current_time = time.time()
        if current_time - self._last_peace_sign_time < self.cooldown_sec:
            return False, None
        
        # Convert BGR to RGB for MediaPipe
        import cv2
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb_frame)
        
        if not results.multi_hand_landmarks:
            return False, None
        
        # Check each detected hand
        for hand_landmarks in results.multi_hand_landmarks:
            landmarks = hand_landmarks.landmark
            
            # MediaPipe hand landmark indices:
            # Index finger: TIP=8, PIP=6, MCP=5
            # Middle finger: TIP=12, PIP=10, MCP=9
            # Ring finger: TIP=16, PIP=14, MCP=13
            # Pinky: TIP=20, PIP=18, MCP=17
            # Thumb: TIP=4, IP=3, MCP=2
            
            # Peace sign: Index and Middle extended, Ring and Pinky folded
            index_extended = self._is_finger_extended(landmarks, 8, 6)
            middle_extended = self._is_finger_extended(landmarks, 12, 10)
            ring_folded = self._is_finger_folded(landmarks, 16, 13)
            pinky_folded = self._is_finger_folded(landmarks, 20, 17)
            
            if index_extended and middle_extended and ring_folded and pinky_folded:
                self._last_peace_sign_time = current_time
                return True, hand_landmarks
        
        return False, None
    
    def draw_landmarks(self, frame, hand_landmarks):
        """Draw hand landmarks on the frame."""
        if MEDIAPIPE_AVAILABLE and hand_landmarks:
            self._mp_draw.draw_landmarks(
                frame, 
                hand_landmarks, 
                self._mp_hands.HAND_CONNECTIONS
            )
        return frame
    
    def close(self):
        """Release resources."""
        if self._hands:
            self._hands.close()
            self._hands = None


# Test script
if __name__ == "__main__":
    import cv2
    
    print("=" * 50)
    print("Gesture Detector Test")
    print("=" * 50)
    print()
    
    if not MEDIAPIPE_AVAILABLE:
        print("ERROR: MediaPipe not installed!")
        print("Install with: pip install mediapipe")
        exit(1)
    
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
            
            # Detect peace sign
            detected, landmarks = detector.detect_peace_sign(frame)
            
            if detected:
                peace_count += 1
                print(f"[{peace_count}] Peace sign detected! ✌️")
            
            # Draw landmarks if detected
            if landmarks:
                detector.draw_landmarks(frame, landmarks)
            
            # Show status
            status = "PEACE SIGN!" if detected else "Watching..."
            color = (0, 255, 0) if detected else (255, 255, 255)
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            cv2.imshow("Gesture Detector Test", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        detector.close()
        cap.release()
        cv2.destroyAllWindows()
        print(f"\nTotal peace signs detected: {peace_count}")
