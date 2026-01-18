"""
Gesture Detector Module (Unified version)

Automatically uses MediaPipe on laptop/desktop, falls back to OpenCV on Pi.
Currently supports: Peace sign (✌️)
"""

import cv2
import numpy as np
import time
import os
from typing import Tuple, Optional

# Audio playback - winsound on Windows (only supports .wav)
try:
    import winsound
    AUDIO_BACKEND = "winsound"
except ImportError:
    AUDIO_BACKEND = None
    print("[GestureDetector] No audio backend available (winsound not found)")

# Sound files directory (same folder as this script)
SOUNDS_DIR = os.path.dirname(os.path.abspath(__file__))

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
    Detects hand gestures and plays associated sounds.
    
    Uses MediaPipe (accurate) if available, otherwise falls back to
    OpenCV skin detection (works on Pi).
    
    Currently supports:
    - Peace sign (✌️ index + middle) -> john.wav (friend)
    - Three fingers (index + middle + ring) -> gerbert.wav
    - Middle finger (🖕) -> enemy.wav
    """
    
    # Gesture to sound file mapping
    GESTURE_SOUNDS = {
        "peace": "john.wav",      # ✌️ Friend
        "three": "gerbert.wav",   # Three fingers
        "middle": "enemy.wav"     # 🖕 Enemy
    }
    
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
        self._use_mediapipe = MEDIAPIPE_AVAILABLE
        
        # Cooldown tracking for each gesture
        self._last_gesture_time = {
            "peace": 0,
            "three": 0,
            "middle": 0
        }
        
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
    
    def _play_sound(self, gesture_name: str):
        """Play the sound file associated with a gesture."""
        sound_file = self.GESTURE_SOUNDS.get(gesture_name)
        if not sound_file:
            return
        
        sound_path = os.path.join(SOUNDS_DIR, sound_file)
        if not os.path.exists(sound_path):
            print(f"[GestureDetector] Sound file not found: {sound_path}")
            return
        
        try:
            if AUDIO_BACKEND == "winsound":
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                print(f"[GestureDetector] No audio backend to play {sound_file}")
        except Exception as e:
            print(f"[GestureDetector] Error playing sound: {e}")
    
    # ==================== MediaPipe Methods ====================
    
    def _is_finger_extended(self, landmarks, tip_idx: int, pip_idx: int) -> bool:
        """Check if finger is extended (MediaPipe)."""
        return landmarks[tip_idx].y < landmarks[pip_idx].y
    
    def _is_finger_folded(self, landmarks, tip_idx: int, mcp_idx: int) -> bool:
        """Check if finger is folded (MediaPipe)."""
        return landmarks[tip_idx].y > landmarks[mcp_idx].y
    
    def _detect_gesture_mediapipe(self, frame) -> Tuple[Optional[str], Optional[object]]:
        """
        Detect gestures using MediaPipe.
        
        Returns:
            Tuple of (gesture_name, hand_landmarks) or (None, None)
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb_frame)
        
        if not results.multi_hand_landmarks:
            return None, None
        
        for hand_landmarks in results.multi_hand_landmarks:
            lm = hand_landmarks.landmark
            
            # Check finger states
            # Index finger (tip=8, pip=6)
            index_extended = self._is_finger_extended(lm, 8, 6)
            # Middle finger (tip=12, pip=10)
            middle_extended = self._is_finger_extended(lm, 12, 10)
            # Ring finger (tip=16, pip=14, mcp=13)
            ring_extended = self._is_finger_extended(lm, 16, 14)
            ring_folded = self._is_finger_folded(lm, 16, 13)
            # Pinky finger (tip=20, pip=18, mcp=17)
            pinky_folded = self._is_finger_folded(lm, 20, 17)
            # Index folded check
            index_folded = self._is_finger_folded(lm, 8, 5)
            
            # Middle finger gesture: ONLY middle extended, others folded
            if (middle_extended and 
                index_folded and 
                ring_folded and 
                pinky_folded):
                return "middle", hand_landmarks
            
            # Three fingers: Index + Middle + Ring extended, Pinky folded
            if (index_extended and 
                middle_extended and 
                ring_extended and 
                pinky_folded):
                return "three", hand_landmarks
            
            # Peace sign: Index + Middle extended, Ring + Pinky folded
            if (index_extended and 
                middle_extended and 
                ring_folded and 
                pinky_folded):
                return "peace", hand_landmarks
        
        return None, None
    
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
    
    # ==================== Public API ====================
    
    def detect_gesture(self, frame) -> Tuple[Optional[str], Optional[object]]:
        """
        Detect any supported gesture in the frame.
        
        Returns:
            Tuple of (gesture_name, landmarks/mask) or (None, None)
            gesture_name can be: "peace", "three", "middle"
        """
        current_time = time.time()
        
        if self._use_mediapipe:
            gesture, data = self._detect_gesture_mediapipe(frame)
        else:
            # OpenCV fallback - count fingers
            gesture, data = self._detect_gesture_opencv(frame)
        
        if gesture:
            # Check cooldown for this specific gesture
            if current_time - self._last_gesture_time[gesture] < self.cooldown_sec:
                return None, data  # Still return data for drawing
            
            # Gesture detected and not on cooldown
            self._last_gesture_time[gesture] = current_time
            self._play_sound(gesture)
            return gesture, data
        
        return None, data
    
    def detect_peace_sign(self, frame) -> Tuple[bool, Optional[object]]:
        """
        Legacy method - detect peace sign gesture.
        
        Returns:
            Tuple of (detected: bool, landmarks/mask for drawing)
        """
        gesture, data = self.detect_gesture(frame)
        return gesture == "peace", data
    
    def _detect_gesture_opencv(self, frame) -> Tuple[Optional[str], Optional[np.ndarray]]:
        """Detect gestures using OpenCV skin detection (fallback)."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_skin, self.upper_skin)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        mask = cv2.erode(mask, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=2)
        mask = cv2.GaussianBlur(mask, (3, 3), 0)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None, mask
        
        max_contour = max(contours, key=cv2.contourArea)
        if cv2.contourArea(max_contour) < self.min_hand_area:
            return None, mask
        
        finger_count = self._count_fingers_opencv(max_contour)
        
        # Map finger count to gesture
        if finger_count == 1:
            return "middle", mask
        elif finger_count == 2:
            return "peace", mask
        elif finger_count == 3:
            return "three", mask
        
        return None, mask
    
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
    
    def get_hand_landmarks(self, frame):
        """
        Get hand landmarks for drawing (always, regardless of gesture).
        
        Returns:
            List of hand landmarks if hands detected, empty list otherwise.
        """
        if not self._use_mediapipe:
            # OpenCV fallback: return skin mask
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, self.lower_skin, self.upper_skin)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
            mask = cv2.erode(mask, kernel, iterations=2)
            mask = cv2.dilate(mask, kernel, iterations=2)
            return [mask] if np.sum(mask) > 0 else []
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            return list(results.multi_hand_landmarks)
        return []
    
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
    
    detector = GestureDetector(cooldown_sec=15.0)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Could not open camera!")
        exit(1)
    
    print("Camera opened. Try these gestures:")
    print("  ✌️  Peace sign (2 fingers) -> john.wav (friend)")
    print("  🤟 Three fingers -> gerbert.wav")
    print("  🖕 Middle finger -> enemy.wav")
    print()
    print("Hand wireframe will always be drawn when hands are visible.")
    print("Press 'q' to quit.")
    print()
    
    gesture_counts = {"peace": 0, "three": 0, "middle": 0}
    gesture_names = {"peace": "FRIEND (John)", "three": "THREE (Gerbert)", "middle": "ENEMY!"}
    gesture_colors = {"peace": (0, 255, 0), "three": (255, 255, 0), "middle": (0, 0, 255)}
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame = cv2.flip(frame, 1)
            
            # Always get and draw hand landmarks
            hand_landmarks = detector.get_hand_landmarks(frame)
            for hand_data in hand_landmarks:
                detector.draw_landmarks(frame, hand_data)
            
            # Check for gestures
            gesture, _ = detector.detect_gesture(frame)
            
            if gesture:
                gesture_counts[gesture] += 1
                emoji = {"peace": "✌️", "three": "🤟", "middle": "🖕"}[gesture]
                print(f"[{sum(gesture_counts.values())}] {gesture.upper()} detected! {emoji}")
            
            # Status display
            mode = "MediaPipe" if MEDIAPIPE_AVAILABLE else "OpenCV"
            hands_status = f" | {len(hand_landmarks)} hand(s)" if hand_landmarks else ""
            
            if gesture:
                status = gesture_names[gesture]
                color = gesture_colors[gesture]
            else:
                status = f"Watching... ({mode}){hands_status}"
                color = (255, 255, 255)
            
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            cv2.imshow("Gesture Detector Test", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        detector.close()
        cap.release()
        cv2.destroyAllWindows()
        print(f"\nGesture counts: {gesture_counts}")
