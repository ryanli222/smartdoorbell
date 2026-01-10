"""
Smart Doorbell API - FastAPI Application

Main entry point for the backend API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .storage import storage
from .routers import events


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    # Startup
    print("[API] Starting up...")
    
    # Initialize database tables
    init_db()
    
    # Ensure MinIO bucket exists
    try:
        storage.ensure_bucket_exists()
    except Exception as e:
        print(f"[API] Warning: Could not initialize storage: {e}")
    
    print("[API] Ready!")
    yield
    
    # Shutdown
    print("[API] Shutting down...")


# Create FastAPI application
app = FastAPI(
    title="Smart Doorbell API",
    description="Backend API for the Smart Door Camera System",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (allow all for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(events.router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "name": "Smart Doorbell API",
        "version": "1.0.0",
        "docs": "/docs"
    }
