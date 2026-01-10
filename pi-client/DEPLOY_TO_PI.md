# Deploy to Raspberry Pi

## 1. Copy Files to Pi

From your Windows machine, copy the `pi-client` folder to your Pi:

```powershell
# Using SCP (replace PI_IP with your Pi's IP address)
scp -r "C:\Users\ryanl\Desktop\Smart Doorbell\pi-client" pi@PI_IP:~/doorcam
```

Or use FileZilla/WinSCP to transfer the folder.

## 2. Install Dependencies on Pi

SSH into your Pi:
```bash
ssh pi@PI_IP
cd ~/doorcam

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install opencv-python RPi.GPIO
```

## 3. Configure Camera Device

On the Pi, find your USB webcam:
```bash
ls /dev/v4l/by-id/
# or
ls /dev/video*
```

Edit `doorcam/config.py` if needed:
```python
CAMERA_DEVICE = "0"  # Change to your camera index
```

## 4. Wire PIR Sensor

Connect PIR sensor to Pi:
- VCC → 5V (Pin 2)
- GND → Ground (Pin 6)
- OUT → GPIO 17 (Pin 11)

## 5. Test Motion Sensor

```bash
# Test with real GPIO
python -m doorcam.motion_sensor
```
Walk in front of the sensor - it should detect motion!

## 6. Test Camera

```bash
python simple_camera_test.py
```

## 7. Test Combined (Motion → Capture)

```bash
python test_motion_camera.py
```

## Quick Test Commands Summary

| Test | Command |
|------|---------|
| Camera only | `python simple_camera_test.py` |
| Motion only | `python -m doorcam.motion_sensor` |
| Combined | `python test_motion_camera.py` |
