from io import BytesIO
from pathlib import Path

from src.common.circuit_breaker import circuits
from src.core.config import settings


class ObjectStorageUnavailable(RuntimeError):
    pass


class ObjectStorageClient:
    def __init__(self):
        self.client = None
        self.local_root = Path(settings.local_media_dir).resolve()

    def connect(self):
        if settings.media_storage_mode == "local":
            self.client = None
            return None
        from minio import Minio
        import urllib3

        http_client = urllib3.PoolManager(timeout=urllib3.Timeout(connect=0.35, read=1.0), retries=False)
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            http_client=http_client,
        )
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
        self.client = client
        return client

    def _require_client(self):
        if self.client:
            return self.client
        return self.connect()

    def _invalidate(self) -> None:
        self.client = None

    def _safe_local_path(self, object_key: str) -> Path:
        target = (self.local_root / object_key).resolve()
        if self.local_root != target and self.local_root not in target.parents:
            raise ValueError("非法的附件路径")
        return target

    def _upload_local(self, object_key: str, data: bytes) -> str:
        target = self._safe_local_path(object_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return object_key

    def _download_local(self, object_key: str) -> bytes:
        target = self._safe_local_path(object_key)
        if not target.is_file():
            raise FileNotFoundError(object_key)
        return target.read_bytes()

    def _forced_minio(self) -> bool:
        return settings.media_storage_mode == "minio"

    def _unavailable(self) -> None:
        raise ObjectStorageUnavailable("MinIO 对象存储不可用")

    def upload_bytes(self, object_key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        if settings.media_storage_mode == "local":
            return self._upload_local(object_key, data)

        def primary() -> str:
            client = self._require_client()
            client.put_object(settings.minio_bucket, object_key, BytesIO(data), len(data), content_type=content_type)
            return object_key

        def fallback() -> str:
            self._invalidate()
            if self._forced_minio():
                self._unavailable()
            return self._upload_local(object_key, data)

        try:
            return circuits.get("minio").execute_sync(primary, fallback)
        except Exception:
            self._invalidate()
            raise

    def download_bytes(self, object_key: str) -> bytes:
        if settings.media_storage_mode == "local":
            return self._download_local(object_key)

        def primary() -> bytes:
            client = self._require_client()
            response = client.get_object(settings.minio_bucket, object_key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        def fallback() -> bytes:
            self._invalidate()
            if self._forced_minio():
                self._unavailable()
            return self._download_local(object_key)

        try:
            return circuits.get("minio").execute_sync(primary, fallback)
        except Exception:
            self._invalidate()
            raise

    def local_path(self, object_key: str) -> Path | None:
        target = self._safe_local_path(object_key)
        return target if target.is_file() else None


object_storage = ObjectStorageClient()
