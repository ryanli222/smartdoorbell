"""
MinIO/S3 storage client and presigned URL generation.
"""

from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from .config import settings


class StorageClient:
    """MinIO storage client for presigned URL generation."""
    
    def __init__(self):
        self._client = None
        self._initialized = False
    
    def _get_client(self) -> Minio:
        """Get or create MinIO client."""
        if self._client is None:
            self._client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure
            )
        return self._client
    
    def ensure_bucket_exists(self):
        """Create the bucket if it doesn't exist."""
        client = self._get_client()
        try:
            if not client.bucket_exists(settings.minio_bucket):
                client.make_bucket(settings.minio_bucket)
                print(f"[Storage] Created bucket: {settings.minio_bucket}")
            else:
                print(f"[Storage] Bucket exists: {settings.minio_bucket}")
            self._initialized = True
        except S3Error as e:
            print(f"[Storage] Error creating bucket: {e}")
            raise
    
    def generate_presigned_upload_url(self, object_name: str) -> str:
        """
        Generate a presigned URL for uploading an object.
        
        Args:
            object_name: Name of the object (file) to upload
            
        Returns:
            Presigned URL for PUT request
        """
        client = self._get_client()
        
        # Generate presigned URL for upload
        url = client.presigned_put_object(
            settings.minio_bucket,
            object_name,
            expires=timedelta(seconds=settings.presigned_url_expiry)
        )
        
        # Replace internal endpoint with external endpoint for client access
        if settings.minio_endpoint != settings.minio_external_endpoint:
            url = url.replace(settings.minio_endpoint, settings.minio_external_endpoint)
        
        return url
    
    def get_object_url(self, object_name: str) -> str:
        """
        Get the public URL for an object.
        
        Args:
            object_name: Name of the object
            
        Returns:
            URL to access the object
        """
        protocol = "https" if settings.minio_secure else "http"
        return f"{protocol}://{settings.minio_external_endpoint}/{settings.minio_bucket}/{object_name}"


# Global storage client instance
storage = StorageClient()
