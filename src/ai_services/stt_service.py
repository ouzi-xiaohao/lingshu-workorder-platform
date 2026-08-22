import asyncio
import tempfile
from pathlib import Path

from src.common.circuit_breaker import circuits
from src.core.config import settings
from src.extensions.minio_client import object_storage


class SpeechToTextService:
    async def transcribe(self, object_key: str) -> str:
        fallback_text = f"音频附件已接收：{Path(object_key).name}"
        if settings.ai_mode not in {"local", "production"}:
            return fallback_text

        async def primary():
            return await asyncio.to_thread(self._transcribe_sync, object_key)

        async def fallback():
            return fallback_text

        return await circuits.get("ai-stt").execute(primary, fallback)

    def _transcribe_sync(self, object_key: str) -> str:
        from faster_whisper import WhisperModel

        local = object_storage.local_path(object_key)
        temporary: str | None = None
        try:
            if local is None:
                suffix = Path(object_key).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                    handle.write(object_storage.download_bytes(object_key))
                    temporary = handle.name
                local = Path(temporary)
            model = WhisperModel(settings.whisper_model, device="auto", compute_type="int8")
            segments, _ = model.transcribe(str(local), language="zh", vad_filter=True)
            text = "".join(segment.text for segment in segments).strip()
            return text or "音频中未识别到清晰语音"
        finally:
            if temporary:
                Path(temporary).unlink(missing_ok=True)
