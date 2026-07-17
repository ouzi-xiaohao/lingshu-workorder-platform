from io import BytesIO

from src.core.config import settings


class ObjectStorageClient:
    def __init__(self):
        self.client = None

    def connect(self):
        try:
            from minio import Minio
            self.client = Minio(settings.minio_endpoint, access_key=settings.minio_access_key, secret_key=settings.minio_secret_key, secure=settings.minio_secure)
            if not self.client.bucket_exists(settings.minio_bucket):
                self.client.make_bucket(settings.minio_bucket)
        except Exception:
            self.client = None
        return self.client

    def upload_bytes(self, object_key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        if not self.client and not self.connect():
            raise RuntimeError("对象存储不可用")
        self.client.put_object(settings.minio_bucket, object_key, BytesIO(data), len(data), content_type=content_type)
        return object_key


object_storage = ObjectStorageClient()
