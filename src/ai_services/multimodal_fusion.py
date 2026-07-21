import json

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
                transcript = await self.stt.transcribe(object_key)
                setattr(attachment, "transcript", transcript)
                evidence.append(transcript)
            elif media_type in {"image", "video"}:
                features = await self.detector.detect(object_key)
                setattr(attachment, "detected_features", json.dumps(features, ensure_ascii=False))
                evidence.extend(features)
        normalized = "；".join(part.strip() for part in evidence if part and part.strip())
        return {"normalized_text": normalized, "media_types": sorted(set(media_types)), "evidence_count": len(evidence)}
