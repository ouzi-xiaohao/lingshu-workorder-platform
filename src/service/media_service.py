from __future__ import annotations

import hashlib
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from src.common.circuit_breaker import CircuitOpenError
from src.common.tracing import traced
from src.core.config import settings
from src.core.error_code import ErrorCode
from src.core.exceptions import BusinessError
from src.extensions.minio_client import ObjectStorageUnavailable, object_storage


ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "audio/mpeg": "audio",
    "audio/wav": "audio",
    "audio/x-wav": "audio",
    "audio/mp4": "audio",
    "audio/ogg": "audio",
    "video/mp4": "video",
    "video/quicktime": "video",
    "video/webm": "video",
}


class MediaValidationError(ValueError):
    pass


class MediaService:
    async def upload(self, file: UploadFile, owner_id: int) -> dict[str, object]:
        async with traced("media.upload", owner_id=owner_id):
            content_type = (file.content_type or mimetypes.guess_type(file.filename or "")[0] or "").lower()
            media_type = ALLOWED_CONTENT_TYPES.get(content_type)
            if not media_type:
                raise MediaValidationError("仅支持 JPG、PNG、WebP、MP3、WAV、M4A、OGG、MP4、MOV、WebM 文件")

            data = await file.read(settings.max_upload_bytes + 1)
            if not data:
                raise MediaValidationError("上传文件不能为空")
            if len(data) > settings.max_upload_bytes:
                raise MediaValidationError(f"单个文件不能超过 {settings.max_upload_bytes // 1024 // 1024} MB")

            suffix = Path(file.filename or "").suffix.lower() or mimetypes.guess_extension(content_type) or ""
            day = datetime.now(timezone.utc).strftime("%Y/%m/%d")
            safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(file.filename or "media").stem).strip("-")[:40] or "media"
            object_key = f"users/{owner_id}/{day}/{uuid4().hex}_{safe_stem}{suffix}"
            try:
                object_storage.upload_bytes(object_key, data, content_type)
            except (ObjectStorageUnavailable, CircuitOpenError) as exc:
                raise BusinessError("对象存储暂时不可用，请稍后重试", ErrorCode.INFRASTRUCTURE_UNAVAILABLE, 503) from exc
            return {
                "media_type": media_type,
                "object_key": object_key,
                "original_name": Path(file.filename or f"upload{suffix}").name[:200],
                "size_bytes": len(data),
                "content_type": content_type,
                "sha256": hashlib.sha256(data).hexdigest(),
            }

    def download(self, object_key: str) -> bytes:
        try:
            return object_storage.download_bytes(object_key)
        except (ObjectStorageUnavailable, CircuitOpenError) as exc:
            raise BusinessError("对象存储暂时不可用，请稍后重试", ErrorCode.INFRASTRUCTURE_UNAVAILABLE, 503) from exc
