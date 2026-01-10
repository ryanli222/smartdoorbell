# Smart Door Camera - Pi Client

Motion detection and camera capture modules for the Raspberry Pi edge device.

## Quick Start

### 1. Install Dependencies

```bash
cd pi-client
pip install -r requirements.txt
```

### 2. Test Camera Preview

Run the camera preview to verify your webcam works:

```bash
python -m doorcam.camera_manager
```

**Controls:**
- Press `q` to quit
- Press `s` to take a snapshot (saved to current directory)

The preview window shows live FPS and resolution info.

### 3. Test Motion Sensor

Run the motion sensor in mock mode (no hardware required):

```bash
python -m doorcam.motion_sensor
```

**Commands:**
- Press `Enter` to simulate motion
- Type `stats` to see detection statistics
- Type `quit` to exit

## Configuration

Set environment variables to customize behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `MOCK_MODE` | `false` | Enable mock mode (no real GPIO/camera) |
| `PIR_GPIO_PIN` | `17` | BCM pin number for PIR sensor |
| `MOTION_DEBOUNCE_MS` | `500` | Hardware debounce time |
| `MOTION_COOLDOWN_SEC` | `5.0` | Minimum time between triggers |
| `CAMERA_DEVICE` | `auto` | Camera path or "auto" |
| `CAMERA_WIDTH` | `1280` | Capture width |
| `CAMERA_HEIGHT` | `720` | Capture height |
| `CAMERA_FPS` | `30` | Target framerate |

## On Raspberry Pi

Install GPIO support:

```bash
pip install RPi.GPIO
```

Wire the PIR sensor:
- VCC → 5V
- GND → GND  
- OUT → GPIO 17 (or configure with `PIR_GPIO_PIN`)

## Troubleshooting

### Camera not found
- Check `ls /dev/video*` to list available devices
- Try setting `CAMERA_DEVICE=0` explicitly
- Ensure no other app is using the camera

### Low FPS
- Reduce resolution: `CAMERA_WIDTH=640 CAMERA_HEIGHT=480`
- Check USB bandwidth (use USB 3.0 port if available)

### Mock mode not working
- Set `MOCK_MODE=true` explicitly
- Or run on a non-Pi machine (auto-detected)
