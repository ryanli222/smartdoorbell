# Smart Doorbell - Backend

Docker Compose backend with FastAPI, PostgreSQL, and MinIO.

## Quick Start

```bash
# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f api
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| api | 8000 | FastAPI application |
| db | 5432 | PostgreSQL database |
| minio | 9000/9001 | S3-compatible storage |

## API Endpoints

- `GET /health` - Health check
- `GET /docs` - Swagger documentation
- `POST /v1/events/start` - Start event, get upload URL
- `POST /v1/events/{id}/finalize` - Finalize with snapshot URL
- `GET /v1/events/{id}` - Get event by ID
- `GET /v1/events/` - List recent events

## MinIO Console

Access at http://localhost:9001

- Username: `minio` (or value of `MINIO_ROOT_USER`)
- Password: `minio_secret` (or value of `MINIO_ROOT_PASSWORD`)

## Development

```bash
# Rebuild API after changes
docker-compose up -d --build api

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```
