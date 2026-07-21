import asyncio
import tempfile
from pathlib import Path

from src.core.config import settings
from src.extensions.minio_client import object_storage


class ImageDetectionService:
    async def detect(self, object_key: str) -> list[str]:
        if settings.ai_mode in {"local", "production"}:
            detected = await asyncio.to_thread(self._detect_sync, object_key)
            if detected:
                return detected
        filename = object_key.lower()
        labels = []
        for keyword in ("smoke", "water", "light", "pump", "aircon"):
            if keyword in filename:
                labels.append(keyword)
        return labels or ["scene_unclassified"]

    def _detect_sync(self, object_key: str) -> list[str]:
        try:
            from ultralytics import YOLO
        except ImportError:
            return []
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
        except Exception:
            return []
        finally:
            if temporary:
                Path(temporary).unlink(missing_ok=True)
