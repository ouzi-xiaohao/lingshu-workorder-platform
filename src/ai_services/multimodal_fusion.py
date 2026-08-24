import json

from src.ai_services.image_detect import ImageDetectionService
from src.ai_services.llm_summary import LLMSummaryService
from src.ai_services.stt_service import SpeechToTextService


class MultimodalFusionService:
    def __init__(self):
        self.stt = SpeechToTextService()
        self.detector = ImageDetectionService()
        self.llm = LLMSummaryService()

    async def fuse(self, title: str, description: str, attachments: list[object], *, heavy: bool = True) -> dict[str, object]:
        evidence: list[str] = []
        for part in (title, description):
            if part and str(part).strip():
                evidence.append(str(part).strip())
        media_types: list[str] = []
        for attachment in attachments:
            media_type = str(getattr(attachment, "media_type", "file"))
            object_key = str(getattr(attachment, "object_key", ""))
            media_types.append(media_type)
            if media_type == "audio":
                transcript = await self.stt.transcribe(object_key) if heavy else f"音频附件待识别：{object_key.rsplit('/', 1)[-1]}"
                setattr(attachment, "transcript", transcript)
                if transcript:
                    evidence.append(f"语音：{transcript}")
            elif media_type in {"image", "video"}:
                features = await self.detector.detect(object_key) if heavy else self.detector._filename_labels(object_key)
                setattr(attachment, "detected_features", json.dumps(features, ensure_ascii=False))
                for feature in features:
                    evidence.append(f"视觉标签：{feature}")
        raw = "；".join(evidence)
        summary = await self.llm.summarize(raw, evidence) if heavy else raw[:180]
        return {
            "normalized_text": summary or raw,
            "evidence": evidence,
            "media_types": sorted(set(media_types)),
            "evidence_count": len(evidence),
            "summary_source": "llm" if heavy else "text",
        }
