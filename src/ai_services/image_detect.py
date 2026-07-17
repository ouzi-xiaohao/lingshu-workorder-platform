class ImageDetectionService:
    async def detect(self, object_key: str) -> list[str]:
        filename = object_key.lower()
        labels = []
        for keyword in ("smoke", "water", "light", "pump", "aircon"):
            if keyword in filename:
                labels.append(keyword)
        return labels or ["scene_unclassified"]
