# Smart Door Camera System Requirements

## 1. Project Overview

This project implements a motion-triggered smart door camera system using a Raspberry Pi with a USB webcam, capable of capturing snapshots and short video clips, running computer-vision inference, and storing structured detection results in a backend system.

The system must be extensible, allowing future integration of hand gesture recognition models without requiring changes to the database schema or public APIs.

## 2. System Goals

- Detect motion using a hardware motion sensor
- Capture camera data only when motion occurs
- Upload snapshots and short clips reliably over unstable networks
- Store metadata and detections in a structured database
- Run OpenCV-based detection today
- Integrate future ML models (e.g., hand gesture recognition) seamlessly
- Separate media storage from metadata storage
- Operate securely and autonomously on boot

## 3. Non-Goals

- Continuous 24/7 video streaming
- Storing raw video blobs directly inside a relational database
- Real-time facial identity verification in the MVP
- Cloud-only dependency (system must run locally)

## 4. Hardware Requirements

### Edge Device

- Raspberry Pi (Pi 4 or newer recommended)
- USB webcam (UVC compliant)
- PIR motion sensor (GPIO)
- Optional: IR illumination or mmWave sensor
- Stable power supply

## 5. Edge Software Requirements (Raspberry Pi)

### Runtime

- Python 3.11+

### Camera

- USB webcam via V4L2
- Accessed using:
  - OpenCV (`cv2.VideoCapture`) for snapshots
  - `ffmpeg` for clip recording

### Motion Detection

- PIR motion sensor via GPIO
- Software debouncing and cooldown logic

### Local Processing

- OpenCV for:
  - Frame capture
  - Person / face / object detection
- Future:
  - Hand landmark detection
  - Gesture classification (MediaPipe / ONNX / TFLite)

### Reliability

- Local event spool on disk
- Automatic retry with exponential backoff
- Graceful recovery from camera disconnects

### Service Management

- Runs as a systemd service
- Auto-restart on failure
- Logs to stdout or journal

## 6. Backend Requirements

### API Service

- FastAPI (preferred) or NestJS
- HTTPS-only access
- Token-based device authentication

### Database

- PostgreSQL
- Use of JSONB for extensible detection metadata
- Optional:
  - pgvector for future embedding similarity search

### Media Storage

- S3-compatible object storage (MinIO)
- Media referenced by URL in database

### Asynchronous Processing

- Redis-backed job queue
- Worker service for ML inference
- Decoupled from API request lifecycle

## 7. Event Lifecycle

1. Motion sensor triggers an event on the edge device
2. Camera captures:
   - One or more snapshots
   - Optional short video clip
3. Event metadata and media are uploaded to backend
4. Backend creates an event record
5. Inference worker processes media
6. Detection results are stored and associated with the event

## 8. Detection & ML Requirements

### Detection Contract (Required)

All detectors must output the following structure:

```json
{
  "type": "person | face | object | gesture",
  "label": "person | package | thumbs_up | open_palm",
  "confidence": 0.0,
  "bbox": { "x": 0, "y": 0, "w": 0, "h": 0 },
  "landmarks": [],
  "embedding": [],
  "extra": {}
}
```

### Gesture Recognition (Future)

- Gesture detection must be implemented as:
  - `type = "gesture"`
  - `label = <gesture_name>`
- Must not require:
  - Database schema changes
  - API changes
- Gesture keypoints must be stored in `landmarks`

## 9. Database Requirements

### Required Tables

- `devices`
- `events`
- `detections`

### Design Constraints

- Events and detections must be relational
- Detection-specific fields must be extensible via JSONB
- Media must be stored outside the database

## 10. Security Requirements

- Per-device API keys
- API keys stored hashed in database
- TLS encryption for all network traffic
- No direct database exposure to edge devices

## 11. Deployment Requirements

- Docker Compose for local deployment
- Separate containers for:
  - API
  - Database
  - Object storage
  - Redis
  - Worker
- Environment-based configuration
- Minimal manual setup steps

## 12. Extensibility Requirements

- New detectors must be added without:
  - Changing API contracts
  - Modifying existing database tables
- Inference pipeline must be configurable per device or event
- Edge and backend inference must be interchangeable

## 13. MVP Success Criteria

- Motion triggers event creation
- Snapshot uploaded and visible in backend
- Event stored correctly in database
- System survives network interruption
- New detection type can be added without refactor
