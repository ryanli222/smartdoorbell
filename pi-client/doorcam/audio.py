"""
Audio Player Module

Plays alert sounds when motion is detected.
Supports WAV, MP3, and other common audio formats.
"""
#imports
import os
import threading
from pathlib import Path
from . import config


def play_audio(file_path: str = None):
    """
    Play an audio file in a background thread.
    
    Args:
        file_path: Path to audio file. Uses config.ALERT_AUDIO_FILE if not provided.
    """
    audio_file = file_path or config.ALERT_AUDIO_FILE
    
    if not audio_file or not Path(audio_file).exists():
        return
    
    def _play():
        try:
            # Try using playsound (cross-platform)
            try:
                from playsound import playsound
                playsound(audio_file)
                return
            except ImportError:
                pass
            
            # Try pygame (more reliable on Pi)
            try:
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)
                return
            except ImportError:
                pass
            
            # Fallback: system command
            import subprocess
            import platform
            
            system = platform.system()
            if system == "Windows":
                # Use PowerShell to play audio on Windows
                subprocess.run(
                    ["powershell", "-c", f"(New-Object Media.SoundPlayer '{audio_file}').PlaySync()"],
                    capture_output=True
                )
            elif system == "Darwin":  # macOS
                subprocess.run(["afplay", audio_file], capture_output=True)
            else:  # Linux
                # Use paplay (PulseAudio) to allow device sharing
                subprocess.run(["paplay", audio_file], capture_output=True)
                    
        except Exception as e:
            print(f"[Audio] Error playing audio: {e}")
    
    # Play in background thread to not block
    thread = threading.Thread(target=_play, daemon=True)
    thread.start()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        print(f"Playing: {sys.argv[1]}")
        play_audio(sys.argv[1])
        print("Done!")
    else:
        print("Usage: python -m doorcam.audio <audio_file>")
