from io import BytesIO
from pathlib import Path

from src.core.config import settings


class ObjectStorageClient:
    def __init__(self):
        self.client = None
        self.local_root = Path(settings.local_media_dir).resolve()

    def connect(self):
        if settings.media_storage_mode == "local":
            return None
        try:
            from minio import Minio
            import urllib3
            http_client = urllib3.PoolManager(timeout=urllib3.Timeout(connect=0.35, read=1.0), retries=False)
            self.client = Minio(settings.minio_endpoint, access_key=settings.minio_access_key, secret_key=settings.minio_secret_key, secure=settings.minio_secure, http_client=http_client)
            if not self.client.bucket_exists(settings.minio_bucket):
                self.client.make_bucket(settings.minio_bucket)
        except Exception:
            self.client = None
        return self.client

    def _safe_local_path(self, object_key: str) -> Path:
        target = (self.local_root / object_key).resolve()
        if self.local_root != target and self.local_root not in target.parents:
            raise ValueError("非法的附件路径")
        return target

    def upload_bytes(self, object_key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        client = self.client or self.connect()
        if client:
            client.put_object(settings.minio_bucket, object_key, BytesIO(data), len(data), content_type=content_type)
            return object_key
        if settings.media_storage_mode == "minio":
            raise RuntimeError("MinIO 对象存储不可用")
        target = self._safe_local_path(object_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return object_key

    def download_bytes(self, object_key: str) -> bytes:
        client = self.client or self.connect()
        if client:
            response = client.get_object(settings.minio_bucket, object_key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        if settings.media_storage_mode == "minio":
            raise RuntimeError("MinIO 对象存储不可用")
        target = self._safe_local_path(object_key)
        if not target.is_file():
            raise FileNotFoundError(object_key)
        return target.read_bytes()

    def local_path(self, object_key: str) -> Path | None:
        target = self._safe_local_path(object_key)
        return target if target.is_file() else None


object_storage = ObjectStorageClient()
