from src.ai_services.image_detect import ImageDetectionService
from src.ai_services.stt_service import SpeechToTextService


class MultimodalFusionService:
    def __init__(self):
        self.stt = SpeechToTextService()
        self.detector = ImageDetectionService()

    async def fuse(self, title: str, description: str, attachments: list[object]) -> dict[str, object]:
        evidence = [title, description]
        media_types: list[str] = []
        for attachment in attachments:
            media_type = str(getattr(attachment, "media_type", "file"))
            object_key = str(getattr(attachment, "object_key", ""))
            media_types.append(media_type)
            if media_type == "audio":
                evidence.append(await self.stt.transcribe(object_key))
            elif media_type in {"image", "video"}:
                evidence.extend(await self.detector.detect(object_key))
        normalized = "；".join(part.strip() for part in evidence if part and part.strip())
        return {"normalized_text": normalized, "media_types": sorted(set(media_types)), "evidence_count": len(evidence)}
