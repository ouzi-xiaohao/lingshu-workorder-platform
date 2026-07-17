from __future__ import annotations

from dataclasses import dataclass
from math import radians, sin, cos, sqrt, atan2


@dataclass(frozen=True)
class WorkerCandidate:
    id: str
    name: str
    skill: str
    longitude: float
    latitude: float
    load: int
    capacity: int
    rating: float


KEYWORDS = {
    "暖通空调": ("空调", "制冷", "温度", "暖气"),
    "设备故障": ("故障", "异响", "损坏", "无法启动", "泵"),
    "照明设施": ("路灯", "照明", "闪烁", "灯不亮"),
    "安全隐患": ("消防", "隐患", "堵塞", "漏电", "烟雾"),
    "环境卫生": ("垃圾", "积水", "异味", "保洁"),
}


def classify_intent(text: str) -> dict[str, object]:
    normalized = text.strip().lower()
    scores = {category: sum(keyword in normalized for keyword in keywords) for category, keywords in KEYWORDS.items()}
    category, hits = max(scores.items(), key=lambda item: item[1])
    if hits == 0:
        category = "综合服务"
    emergency = any(word in normalized for word in ("消防", "漏电", "被困", "大量积水", "紧急"))
    high = emergency or any(word in normalized for word in ("故障", "无法", "堵塞"))
    priority = "紧急" if emergency else "高" if high else "中"
    confidence = min(0.98, 0.72 + hits * 0.09)
    return {"category": category, "priority": priority, "confidence": round(confidence, 2)}


def _distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6371.0
    dlon, dlat = radians(lon2 - lon1), radians(lat2 - lat1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return radius * 2 * atan2(sqrt(a), sqrt(1 - a))


def choose_worker(category: str, longitude: float, latitude: float, workers: list[WorkerCandidate]) -> dict[str, object] | None:
    available = [worker for worker in workers if worker.load < worker.capacity]
    if not available:
        return None
    ranked = []
    for worker in available:
        distance = _distance_km(longitude, latitude, worker.longitude, worker.latitude)
        skill_score = 1.0 if category in worker.skill or worker.skill in category else 0.55
        load_score = 1 - worker.load / worker.capacity
        distance_score = max(0.0, 1 - distance / 20)
        score = skill_score * 0.45 + load_score * 0.25 + distance_score * 0.2 + (worker.rating / 100) * 0.1
        ranked.append((score, distance, worker))
    score, distance, worker = max(ranked, key=lambda item: item[0])
    return {"worker_id": worker.id, "worker_name": worker.name, "score": round(score, 3), "distance_km": round(distance, 2)}
