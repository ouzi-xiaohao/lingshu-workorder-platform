import asyncio
import tempfile
from pathlib import Path

from src.common.circuit_breaker import circuits
from src.core.config import settings
from src.extensions.minio_client import object_storage


class ImageDetectionService:
    async def detect(self, object_key: str) -> list[str]:
        filename_labels = self._filename_labels(object_key)

        async def fallback():
            return filename_labels or ["scene_unclassified"]

        if settings.ai_mode not in {"local", "production"}:
            return await fallback()

        async def primary():
            return await asyncio.to_thread(self._detect_sync, object_key)

        detected = await circuits.get("ai-vision").execute(primary, fallback)
        return detected or filename_labels or ["scene_unclassified"]

    def _filename_labels(self, object_key: str) -> list[str]:
        filename = object_key.lower()
        return [keyword for keyword in ("smoke", "water", "light", "pump", "aircon") if keyword in filename]

    def _detect_sync(self, object_key: str) -> list[str]:
        from ultralytics import YOLO

        local = object_storage.local_path(object_key)
        temporary: str | None = None
        try:
            if local is None:
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(object_key).suffix) as handle:
                    handle.write(object_storage.download_bytes(object_key))
                    temporary = handle.name
                local = Path(temporary)
            model = YOLO(settings.yolo_model)
            results = model.predict(source=str(local), verbose=False, vid_stride=30)
            labels = {
                result.names[int(class_id)]
                for result in results
                for class_id in result.boxes.cls.tolist()
            }
            return sorted(labels)
        finally:
            if temporary:
                Path(temporary).unlink(missing_ok=True)
