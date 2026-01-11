# Smart Door Camera - Pi Client

Camera-based motion detection and live display for the Raspberry Pi doorbell system.  
**No external motion sensor required** - uses frame differencing with the USB webcam.

## Quick Start

### 1. Install Dependencies

```bash
cd pi-client
pip install -r requirements.txt
```

### 2. Quick Camera Test

Test that your camera is working:

```bash
python simple_camera_test.py
```

Press `q` to quit.

### 3. Motion-Triggered Live Display ⭐

This is the main application - shows a fullscreen camera feed when motion is detected:

```bash
python -m doorcam.live_display
```

**What it does:**
- Monitors camera for motion using frame differencing
- Shows fullscreen "LIVE" camera view for 15 seconds when motion detected
- Plays doorbell audio alert
- Takes snapshot 3 seconds after motion and uploads to backend
- Relays microphone audio through speakers during active session

**Options:**
```bash
python -m doorcam.live_display --help
```

| Option | Default | Description |
|--------|---------|-------------|
| `--audio <path>` | `alerts/doorbell.wav` | Audio file to play on motion |
| `--duration <sec>` | `15` | How long to show camera |
| `--snapshot-delay <sec>` | `3` | Delay before taking snapshot |
| `--sensitivity <val>` | `25` | Motion threshold (lower = more sensitive) |
| `--min-area <px>` | `5000` | Minimum motion area to trigger |
| `--backend <url>` | `$BACKEND_URL` | Backend URL for snapshot upload |

**Runtime Controls:**
- Press `q` to quit
- Press `f` to pause detection for 60 seconds (press again to cancel)

### 4. Test Camera Motion Detection

Test motion detection alone (without upload):

```bash
python -m doorcam.camera_motion
```

Shows preview window with motion status and sensitivity stats.  
Press `q` to quit.

### 5. Test Audio Relay

Test microphone-to-speaker passthrough:

```bash
python -m doorcam.audio_relay
```

Press `Ctrl+C` to stop.

## Configuration

Set environment variables to customize behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMERA_DEVICE` | `auto` | Camera path or "auto" |
| `CAMERA_WIDTH` | `1920` | Capture width |
| `CAMERA_HEIGHT` | `1080` | Capture height |
| `CAMERA_FPS` | `30` | Target framerate |
| `ALERT_AUDIO_FILE` | `alerts/doorbell.wav` | Audio alert on motion |
| `BACKEND_URL` | `http://localhost:8000` | Backend API URL |
| `MOCK_MODE` | `false` | Enable mock mode (no camera) |

## Project Structure

```
pi-client/
├── doorcam/
│   ├── live_display.py    # Main entry point - motion triggered display
│   ├── camera_motion.py   # Camera-based motion detection
│   ├── camera_manager.py  # Camera handling wrapper
│   ├── audio.py           # Audio alert playback
│   ├── audio_relay.py     # Mic-to-speaker passthrough
│   └── config.py          # Configuration from env vars
├── alerts/
│   └── doorbell.wav       # Default doorbell sound
├── requirements.txt
└── README.md
```

## On Raspberry Pi

See [DEPLOY_TO_PI.md](DEPLOY_TO_PI.md) for full deployment instructions.

Quick setup:
```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3-opencv portaudio19-dev

# Install Python packages
pip install -r requirements.txt

# Run
export BACKEND_URL="https://your-ngrok-url.ngrok-free.app"
python -m doorcam.live_display
```

## Troubleshooting

### Camera not found
- Check `ls /dev/video*` to list available devices
- Try setting `CAMERA_DEVICE=0` explicitly
- Ensure no other app is using the camera

### Low FPS
- Reduce resolution: `CAMERA_WIDTH=640 CAMERA_HEIGHT=480`
- Check USB bandwidth (use USB 3.0 port if available)

### Audio not playing
- Ensure audio file exists: `alerts/doorbell.wav`
- Install an audio backend: `pip install playsound` or `pip install pygame`
- On Linux: install `aplay` for WAV files

### PyAudio installation issues
On Windows:
```bash
pip install pipwin
pipwin install pyaudio
```

On Linux:
```bash
sudo apt install portaudio19-dev
pip install pyaudio
```
