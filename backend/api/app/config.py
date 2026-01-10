"""
Configuration settings for the Smart Doorbell API.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://doorbell:doorbell_secret@localhost:5432/doorbell"
    )
    
    # MinIO
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minio")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minio_secret")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "doorbell-snapshots")
    minio_external_endpoint: str = os.getenv("MINIO_EXTERNAL_ENDPOINT", "localhost:9000")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    
    # Presigned URL expiry (seconds)
    presigned_url_expiry: int = int(os.getenv("PRESIGNED_URL_EXPIRY", "3600"))

    class Config:
        env_file = ".env"


settings = Settings()
