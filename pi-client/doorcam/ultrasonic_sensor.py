"""
Ultrasonic Sensor Module (HC-SR04)

Detects presence/motion using distance measurement.
Triggers when distance drops below threshold (someone approaching).
"""

import time
import threading
from typing import Callable, Optional

# Try to import RPi.GPIO
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    GPIO = None


class UltrasonicSensor:
    """
    HC-SR04 Ultrasonic distance sensor for motion detection.
    
    Triggers callback when distance drops below threshold.
    
    Wiring:
        VCC  -> 5V
        GND  -> Ground
        TRIG -> GPIO 23 (or configured pin)
        ECHO -> GPIO 24 (or configured pin) - USE VOLTAGE DIVIDER!
    
    IMPORTANT: ECHO pin outputs 5V but Pi GPIO is 3.3V!
    Use a voltage divider: ECHO -> 1k resistor -> GPIO -> 2k resistor -> GND
    """
    
    def __init__(
        self,
        callback: Callable[[], None],
        trig_pin: int = 23,
        echo_pin: int = 24,
        trigger_distance_cm: float = 100.0,
        cooldown_sec: float = 3.0,
        poll_interval_sec: float = 0.2
    ):
        """
        Initialize ultrasonic sensor.
        
        Args:
            callback: Function to call when motion detected
            trig_pin: GPIO pin for TRIG (BCM mode)
            echo_pin: GPIO pin for ECHO (BCM mode)
            trigger_distance_cm: Trigger when distance < this value
            cooldown_sec: Minimum time between triggers
            poll_interval_sec: How often to measure distance
        """
        self.callback = callback
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.trigger_distance_cm = trigger_distance_cm
        self.cooldown_sec = cooldown_sec
        self.poll_interval_sec = poll_interval_sec
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_trigger_time = 0
        
        # Stats
        self.trigger_count = 0
        self.last_distance = 0.0
    
    def _setup_gpio(self):
        """Initialize GPIO pins."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        GPIO.output(self.trig_pin, False)
        time.sleep(0.5)  # Let sensor settle
    
    def measure_distance(self) -> float:
        """
        Measure distance in centimeters.
        
        Returns:
            Distance in cm, or -1 if measurement failed
        """
        if not GPIO_AVAILABLE:
            return -1
        
        # Send trigger pulse
        GPIO.output(self.trig_pin, True)
        time.sleep(0.00001)  # 10 microseconds
        GPIO.output(self.trig_pin, False)
        
        # Wait for echo start
        pulse_start = time.time()
        timeout = pulse_start + 0.1  # 100ms timeout
        
        while GPIO.input(self.echo_pin) == 0:
            pulse_start = time.time()
            if pulse_start > timeout:
                return -1
        
        # Wait for echo end
        pulse_end = time.time()
        timeout = pulse_end + 0.1
        
        while GPIO.input(self.echo_pin) == 1:
            pulse_end = time.time()
            if pulse_end > timeout:
                return -1
        
        # Calculate distance
        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150  # Speed of sound / 2
        distance = round(distance, 2)
        
        return distance
    
    def _poll_loop(self):
        """Background polling loop."""
        print(f"[Ultrasonic] Polling started (trigger < {self.trigger_distance_cm}cm)")
        
        while self._running:
            distance = self.measure_distance()
            self.last_distance = distance
            
            if distance > 0:
                # Check if someone is within trigger distance
                if distance < self.trigger_distance_cm:
                    current_time = time.time()
                    time_since_last = current_time - self._last_trigger_time
                    
                    if time_since_last >= self.cooldown_sec:
                        self._last_trigger_time = current_time
                        self.trigger_count += 1
                        print(f"[Ultrasonic] MOTION! Distance: {distance}cm (trigger #{self.trigger_count})")
                        
                        try:
                            self.callback()
                        except Exception as e:
                            print(f"[Ultrasonic] Callback error: {e}")
            
            time.sleep(self.poll_interval_sec)
    
    def start(self):
        """Start the sensor polling."""
        if self._running:
            print("[Ultrasonic] Already running")
            return
        
        if not GPIO_AVAILABLE:
            print("[Ultrasonic] ERROR: RPi.GPIO not available!")
            return
        
        print(f"[Ultrasonic] Starting on TRIG={self.trig_pin}, ECHO={self.echo_pin}")
        self._setup_gpio()
        
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        print("[Ultrasonic] Ready")
    
    def stop(self):
        """Stop the sensor."""
        if not self._running:
            return
        
        print("[Ultrasonic] Stopping...")
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        
        print("[Ultrasonic] Stopped")
    
    def get_stats(self) -> dict:
        """Get sensor statistics."""
        return {
            "trigger_count": self.trigger_count,
            "last_distance_cm": self.last_distance,
            "trigger_threshold_cm": self.trigger_distance_cm,
            "running": self._running,
            "trig_pin": self.trig_pin,
            "echo_pin": self.echo_pin
        }


# Test script
if __name__ == "__main__":
    print("=" * 50)
    print("HC-SR04 Ultrasonic Sensor Test")
    print("=" * 50)
    print()
    print("Wiring:")
    print("  VCC  -> 5V")
    print("  GND  -> Ground")
    print("  TRIG -> GPIO 23")
    print("  ECHO -> GPIO 24 (with voltage divider!)")
    print()
    
    def on_motion():
        print("\n*** MOTION DETECTED! ***\n")
    
    sensor = UltrasonicSensor(
        callback=on_motion,
        trigger_distance_cm=50.0  # Trigger when < 50cm
    )
    
    sensor.start()
    
    print("Watching for motion (Ctrl+C to stop)...")
    print("Move your hand in front of the sensor.")
    print()
    
    try:
        while True:
            print(f"Distance: {sensor.last_distance:.1f} cm", end="\r")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        sensor.stop()
        print("\nFinal stats:", sensor.get_stats())
