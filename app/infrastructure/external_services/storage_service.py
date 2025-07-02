"""Storage service using MinIO"""

from minio import Minio
from minio.error import S3Error
import uuid
from typing import BinaryIO, Union
from io import BytesIO

from ...core.config import settings


class StorageService:
    
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket = settings.MINIO_BUCKET_NAME
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure bucket exists"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error:
            pass  # Bucket might already exist
    
    async def upload_file(self, file_data: Union[BinaryIO, bytes], filename: str, content_type: str) -> str:
        """Upload file and return URL"""
        try:
            # Generate unique filename
            unique_name = f"{uuid.uuid4().hex}_{filename}"
            
            # Handle both BinaryIO and raw bytes
            if isinstance(file_data, bytes):
                file_stream = BytesIO(file_data)
                file_size = len(file_data)
            else:
                file_stream = file_data
                # Get file size
                file_stream.seek(0, 2)
                file_size = file_stream.tell()
                file_stream.seek(0)
            
            # Upload
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=unique_name,
                data=file_stream,
                length=file_size,
                content_type=content_type
            )
            
            # Return URL
            protocol = "https" if settings.MINIO_SECURE else "http"
            return f"{protocol}://{settings.MINIO_ENDPOINT}/{self.bucket}/{unique_name}"
        except Exception as e:
            raise Exception(f"Failed to upload file: {e}")
    
    async def delete_file(self, file_url: str) -> bool:
        """Delete file by URL"""
        try:
            # Extract object name from URL
            object_name = file_url.split('/')[-1]
            self.client.remove_object(self.bucket, object_name)
            return True
        except Exception:
            return False
    
    async def get_presigned_url(self, file_url: str, expires_seconds: int = 3600) -> str:
        """Get presigned URL for private access"""
        try:
            from datetime import timedelta
            object_name = file_url.split('/')[-1]
            return self.client.presigned_get_object(
                bucket_name=self.bucket,
                object_name=object_name,
                expires=timedelta(seconds=expires_seconds)
            )
        except Exception:
            return file_url  # Return original if presigned fails 