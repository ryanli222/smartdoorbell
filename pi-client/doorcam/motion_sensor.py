"""
Motion Sensor Module

Handles PIR motion sensor input via GPIO with software debouncing.
Supports mock mode for development on non-Pi machines.
"""

import time
import threading
from typing import Callable, Optional
from . import config

# Try to import RPi.GPIO, fall back to mock if unavailable
try:
    if config.MOCK_MODE:
        raise ImportError("Mock mode enabled")
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    GPIO = None


class MockGPIO:
    """Mock GPIO for development without real hardware."""
    BCM = "BCM"
    IN = "IN"
    PUD_DOWN = "PUD_DOWN"
    RISING = "RISING"
    
    _callbacks = {}
    _running = False
    _trigger_thread = None
    
    @classmethod
    def setmode(cls, mode):
        print(f"[MockGPIO] setmode({mode})")
    
    @classmethod
    def setup(cls, pin, direction, pull_up_down=None):
        print(f"[MockGPIO] setup(pin={pin}, direction={direction})")
    
    @classmethod
    def add_event_detect(cls, pin, edge, callback=None, bouncetime=None):
        print(f"[MockGPIO] add_event_detect(pin={pin}, edge={edge}, bouncetime={bouncetime})")
        if callback:
            cls._callbacks[pin] = callback
    
    @classmethod
    def remove_event_detect(cls, pin):
        print(f"[MockGPIO] remove_event_detect(pin={pin})")
        cls._callbacks.pop(pin, None)
    
    @classmethod
    def cleanup(cls):
        print("[MockGPIO] cleanup()")
        cls._running = False
        cls._callbacks.clear()
    
    @classmethod
    def simulate_motion(cls, pin):
        """Simulate a motion trigger for testing."""
        if pin in cls._callbacks:
            print(f"[MockGPIO] Simulating motion on pin {pin}")
            cls._callbacks[pin](pin)
    
    @classmethod
    def start_random_triggers(cls, pin, interval_sec=10):
        """Start a background thread that triggers motion periodically."""
        cls._running = True
        def trigger_loop():
            while cls._running:
                time.sleep(interval_sec)
                if cls._running and pin in cls._callbacks:
                    cls.simulate_motion(pin)
        cls._trigger_thread = threading.Thread(target=trigger_loop, daemon=True)
        cls._trigger_thread.start()
        print(f"[MockGPIO] Started random triggers every {interval_sec}s on pin {pin}")


class MotionSensor:
    """
    PIR Motion Sensor handler with debouncing and cooldown.
    
    Usage:
        sensor = MotionSensor(callback=on_motion)
        sensor.start()
        # ... run your app ...
        sensor.stop()
    """
    
    def __init__(
        self,
        callback: Callable[[], None],
        pin: int = None,
        debounce_ms: int = None,
        cooldown_sec: float = None,
        mock_mode: bool = None
    ):
        """
        Initialize motion sensor.
        
        Args:
            callback: Function to call when motion is detected
            pin: GPIO pin number (BCM mode)
            debounce_ms: Hardware debounce time in milliseconds
            cooldown_sec: Minimum time between triggers
            mock_mode: Force mock mode (auto-detected if None)
        """
        self.pin = pin or config.PIR_GPIO_PIN
        self.debounce_ms = debounce_ms or config.MOTION_DEBOUNCE_MS
        self.cooldown_sec = cooldown_sec or config.MOTION_COOLDOWN_SEC
        self.callback = callback
        
        # Determine if we should use mock mode
        if mock_mode is not None:
            self.mock_mode = mock_mode
        else:
            self.mock_mode = config.MOCK_MODE or not GPIO_AVAILABLE
        
        self._gpio = MockGPIO if self.mock_mode else GPIO
        self._last_trigger_time = 0
        self._running = False
        self._lock = threading.Lock()
        
        # Statistics
        self.trigger_count = 0
        self.filtered_count = 0
    
    def _on_motion_detected(self, channel):
        """Internal callback for GPIO edge detection."""
        current_time = time.time()
        
        with self._lock:
            time_since_last = current_time - self._last_trigger_time
            
            if time_since_last < self.cooldown_sec:
                self.filtered_count += 1
                print(f"[MotionSensor] Motion filtered (cooldown: {time_since_last:.1f}s < {self.cooldown_sec}s)")
                return
            
            self._last_trigger_time = current_time
            self.trigger_count += 1
        
        print(f"[MotionSensor] Motion detected! (trigger #{self.trigger_count})")
        
        # Call user callback
        try:
            self.callback()
        except Exception as e:
            print(f"[MotionSensor] Error in callback: {e}")
    
    def start(self):
        """Start listening for motion events."""
        if self._running:
            print("[MotionSensor] Already running")
            return
        
        print(f"[MotionSensor] Starting on GPIO pin {self.pin} (mock={self.mock_mode})")
        
        if not self.mock_mode:
            self._gpio.setmode(self._gpio.BCM)
            self._gpio.setup(self.pin, self._gpio.IN, pull_up_down=self._gpio.PUD_DOWN)
        else:
            self._gpio.setmode(self._gpio.BCM)
            self._gpio.setup(self.pin, self._gpio.IN)
        
        self._gpio.add_event_detect(
            self.pin,
            self._gpio.RISING,
            callback=self._on_motion_detected,
            bouncetime=self.debounce_ms
        )
        
        self._running = True
        print("[MotionSensor] Ready and listening for motion")
    
    def stop(self):
        """Stop listening for motion events."""
        if not self._running:
            return
        
        print("[MotionSensor] Stopping...")
        self._gpio.remove_event_detect(self.pin)
        self._gpio.cleanup()
        self._running = False
        print("[MotionSensor] Stopped")
    
    def simulate_motion(self):
        """Manually trigger a motion event (for testing)."""
        if self.mock_mode:
            self._gpio.simulate_motion(self.pin)
        else:
            # Directly call the motion handler
            self._on_motion_detected(self.pin)
    
    def get_stats(self) -> dict:
        """Get motion detection statistics."""
        return {
            "trigger_count": self.trigger_count,
            "filtered_count": self.filtered_count,
            "running": self._running,
            "mock_mode": self.mock_mode,
            "pin": self.pin
        }


# Simple test script
if __name__ == "__main__":
    import sys
    
    print("=" * 50)
    print("Motion Sensor Test")
    print("=" * 50)
    
    def on_motion():
        print("\n*** MOTION DETECTED! ***\n")
    
    sensor = MotionSensor(callback=on_motion, mock_mode=True)
    sensor.start()
    
    print("\nCommands:")
    print("  Press ENTER to simulate motion")
    print("  Type 'stats' to see statistics")
    print("  Type 'quit' to exit")
    print()
    
    try:
        while True:
            cmd = input("> ").strip().lower()
            if cmd == "quit" or cmd == "q":
                break
            elif cmd == "stats":
                print(sensor.get_stats())
            else:
                sensor.simulate_motion()
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        sensor.stop()
        print("\nFinal stats:", sensor.get_stats())
