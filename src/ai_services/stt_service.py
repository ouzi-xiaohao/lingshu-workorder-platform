class SpeechToTextService:
    async def transcribe(self, object_key: str) -> str:
        return f"[语音待转写] {object_key}"
