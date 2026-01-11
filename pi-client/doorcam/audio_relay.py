"""
Audio Relay Module

Captures audio from microphone and plays it through speakers in real-time.
Uses subprocess with arecord/aplay for better Raspberry Pi compatibility.
"""

import subprocess
import threading
import time
import platform


class AudioRelay:
    """
    Real-time audio passthrough from microphone to speakers.
    
    Uses arecord/aplay on Linux (Pi) for reliable webcam mic support.
    Falls back to PyAudio on Windows/Mac.
    """
    
    def __init__(self, device: str = None):
        """
        Initialize audio relay.
        
        Args:
            device: ALSA device name (e.g., "plughw:JVCU100,0") or None for auto-detect
        """
        self.device = device
        self._running = False
        self._process = None
        self._thread = None
    
    def _find_webcam_device(self) -> str:
        """Find the webcam audio device."""
        try:
            result = subprocess.run(
                ["arecord", "-l"],
                capture_output=True,
                text=True
            )
            
            # Parse output for webcam/USB device
            for line in result.stdout.split('\n'):
                if 'card' in line.lower():
                    # Extract card name
                    if 'usb' in line.lower() or 'webcam' in line.lower() or 'jvcu' in line.lower():
                        # Extract card number or name
                        parts = line.split(':')
                        if len(parts) >= 2:
                            card_part = parts[0]
                            card_num = ''.join(filter(str.isdigit, card_part))
                            if card_num:
                                return f"plughw:{card_num},0"
            
            # Default fallback
            return "plughw:1,0"
        except:
            return "plughw:1,0"
    
    def _relay_loop_linux(self):
        """Audio relay using arecord | aplay (Linux/Pi)."""
        device = self.device or self._find_webcam_device()
        
        print(f"[AudioRelay] Starting with device: {device}")
        
        try:
            # Use arecord piped to aplay for real-time relay
            # -D = device, -f cd = CD quality, -t raw = raw format
            self._process = subprocess.Popen(
                f"arecord -D {device} -f cd -t raw 2>/dev/null | aplay -f cd -t raw 2>/dev/null",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Create new process group for proper cleanup
            )
            
            print("[AudioRelay] Started - mic → speakers")
            
            # Wait for process or stop signal
            while self._running:
                if self._process.poll() is not None:
                    # Process ended unexpectedly
                    if self._running:
                        print("[AudioRelay] Process ended, restarting...")
                        time.sleep(0.5)
                        self._process = subprocess.Popen(
                            f"arecord -D {device} -f cd -t raw 2>/dev/null | aplay -f cd -t raw 2>/dev/null",
                            shell=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                time.sleep(0.1)
                
        except Exception as e:
            print(f"[AudioRelay] Error: {e}")
        finally:
            self._cleanup()
    
    def _relay_loop_pyaudio(self):
        """Audio relay using PyAudio (Windows/Mac)."""
        try:
            import pyaudio
            
            p = pyaudio.PyAudio()
            
            # Find input device
            input_device = None
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    name = info['name'].lower()
                    if 'usb' in name or 'webcam' in name or 'camera' in name:
                        input_device = i
                        print(f"[AudioRelay] Using: {info['name']}")
                        break
            
            # Open streams
            stream_in = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                input_device_index=input_device,
                frames_per_buffer=1024
            )
            
            stream_out = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                output=True,
                frames_per_buffer=1024
            )
            
            print("[AudioRelay] Started - mic → speakers")
            
            while self._running:
                try:
                    data = stream_in.read(1024, exception_on_overflow=False)
                    stream_out.write(data)
                except:
                    break
            
            stream_in.close()
            stream_out.close()
            p.terminate()
            
        except ImportError:
            print("[AudioRelay] PyAudio not available")
        except Exception as e:
            print(f"[AudioRelay] Error: {e}")
    
    def _cleanup(self):
        """Clean up processes."""
        if self._process:
            try:
                # Use pkill to kill arecord and aplay processes we started
                subprocess.run(["pkill", "-f", "arecord.*aplay"], capture_output=True)
            except:
                pass
            try:
                self._process.kill()
                self._process.wait(timeout=1)
            except:
                pass
            self._process = None
    
    def start(self):
        """Start audio relay in background thread."""
        if self._running:
            return
        
        self._running = True
        
        # Choose method based on platform
        if platform.system() == "Linux":
            target = self._relay_loop_linux
        else:
            target = self._relay_loop_pyaudio
        
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop audio relay."""
        if not self._running:
            return
        
        print("[AudioRelay] Stopping...")
        self._running = False
        self._cleanup()
        
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        
        print("[AudioRelay] Stopped")
    
    def is_running(self) -> bool:
        """Check if relay is running."""
        return self._running


# Convenience functions
_relay = None

def start_audio_relay(device: str = None):
    """Start the global audio relay."""
    global _relay
    if _relay is None:
        _relay = AudioRelay(device=device)
    _relay.start()

def stop_audio_relay():
    """Stop the global audio relay."""
    global _relay
    if _relay:
        _relay.stop()


if __name__ == "__main__":
    import sys
    
    print("=" * 50)
    print("Audio Relay Test")
    print("=" * 50)
    print()
    
    # Allow specifying device on command line
    device = sys.argv[1] if len(sys.argv) > 1 else None
    
    if device:
        print(f"Using device: {device}")
    else:
        print("Auto-detecting webcam device...")
    print()
    print("Speak into your webcam mic - you should hear yourself!")
    print("Press Ctrl+C to stop.")
    print()
    
    relay = AudioRelay(device=device)
    relay.start()
    
    try:
        while relay.is_running():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        relay.stop()
