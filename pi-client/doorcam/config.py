# Pi Client Configuration

import os

# GPIO Configuration
PIR_GPIO_PIN = int(os.getenv("PIR_GPIO_PIN", "17"))  # BCM pin number
MOTION_DEBOUNCE_MS = int(os.getenv("MOTION_DEBOUNCE_MS", "500"))
MOTION_COOLDOWN_SEC = float(os.getenv("MOTION_COOLDOWN_SEC", "5.0"))

# Camera Configuration
CAMERA_DEVICE = os.getenv("CAMERA_DEVICE", "auto")  # "auto" or specific path like /dev/video0
CAMERA_WIDTH = int(os.getenv("CAMERA_WIDTH", "1920"))
CAMERA_HEIGHT = int(os.getenv("CAMERA_HEIGHT", "1080"))
CAMERA_FPS = int(os.getenv("CAMERA_FPS", "30"))
CAMERA_WARMUP_FRAMES = int(os.getenv("CAMERA_WARMUP_FRAMES", "10"))

# Mock mode for development (no real GPIO/camera)
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
