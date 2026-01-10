"""
Audio Relay Module

Captures audio from microphone and plays it through speakers in real-time.
Used for live audio monitoring during motion events.
"""

import threading
import time


class AudioRelay:
    """
    Real-time audio passthrough from microphone to speakers.
    
    Uses PyAudio for cross-platform audio streaming.
    """
    
    def __init__(self, device_index: int = None, chunk_size: int = 1024, sample_rate: int = 44100):
        """
        Initialize audio relay.
        
        Args:
            device_index: Input device index (None = default microphone)
            chunk_size: Audio buffer size
            sample_rate: Sample rate in Hz
        """
        self.device_index = device_index
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        
        self._running = False
        self._thread = None
        self._pyaudio = None
        self._stream_in = None
        self._stream_out = None
    
    def _relay_loop(self):
        """Main audio relay loop."""
        try:
            import pyaudio
            
            self._pyaudio = pyaudio.PyAudio()
            
            # Find the webcam microphone if device_index not specified
            input_device = self.device_index
            if input_device is None:
                # List audio devices and try to find webcam
                for i in range(self._pyaudio.get_device_count()):
                    info = self._pyaudio.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        name = info['name'].lower()
                        # Prefer USB/webcam devices
                        if 'usb' in name or 'webcam' in name or 'camera' in name:
                            input_device = i
                            print(f"[AudioRelay] Using input: {info['name']}")
                            break
                
                # Fallback to default
                if input_device is None:
                    input_device = self._pyaudio.get_default_input_device_info()['index']
                    print(f"[AudioRelay] Using default input device")
            
            # Open input stream (microphone)
            self._stream_in = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=input_device,
                frames_per_buffer=self.chunk_size
            )
            
            # Open output stream (speakers)
            self._stream_out = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size
            )
            
            print("[AudioRelay] Started - mic → speakers")
            
            # Relay loop
            while self._running:
                try:
                    # Read from mic
                    data = self._stream_in.read(self.chunk_size, exception_on_overflow=False)
                    # Write to speakers
                    self._stream_out.write(data)
                except Exception as e:
                    if self._running:
                        print(f"[AudioRelay] Stream error: {e}")
                    break
            
        except ImportError:
            print("[AudioRelay] PyAudio not installed. Run: pip install pyaudio")
        except Exception as e:
            print(f"[AudioRelay] Error: {e}")
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up audio streams."""
        if self._stream_in:
            try:
                self._stream_in.stop_stream()
                self._stream_in.close()
            except:
                pass
            self._stream_in = None
        
        if self._stream_out:
            try:
                self._stream_out.stop_stream()
                self._stream_out.close()
            except:
                pass
            self._stream_out = None
        
        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except:
                pass
            self._pyaudio = None
    
    def start(self):
        """Start audio relay in background thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._relay_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop audio relay."""
        if not self._running:
            return
        
        print("[AudioRelay] Stopping...")
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        
        self._cleanup()
        print("[AudioRelay] Stopped")
    
    def is_running(self) -> bool:
        """Check if relay is running."""
        return self._running


# Global instance for easy access
_relay = None


def start_audio_relay():
    """Start the global audio relay."""
    global _relay
    if _relay is None:
        _relay = AudioRelay()
    _relay.start()


def stop_audio_relay():
    """Stop the global audio relay."""
    global _relay
    if _relay:
        _relay.stop()


if __name__ == "__main__":
    print("=" * 50)
    print("Audio Relay Test")
    print("=" * 50)
    print()
    print("This will relay audio from your microphone to speakers.")
    print("Press Ctrl+C to stop.")
    print()
    
    relay = AudioRelay()
    relay.start()
    
    try:
        while relay.is_running():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        relay.stop()
