from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.geo_calc import haversine_km


@dataclass(frozen=True)
class RankedWorker:
    user_id: int
    display_name: str
    score: float
    distance_km: float
    decision_factors: dict[str, float]


def _skill_match(category: str, skills: str) -> bool:
    tokens = [item.strip() for item in str(skills).replace("/", ",").split(",") if item.strip()]
    return category in tokens


def rank_worker_candidates(
    *,
    category: str,
    longitude: float,
    latitude: float,
    candidates: list[dict[str, Any]],
    limit: int = 3,
) -> list[RankedWorker]:
    ranked: list[RankedWorker] = []
    for candidate in candidates:
        if candidate["current_load"] >= candidate["max_load"]:
            continue
        distance = haversine_km(longitude, latitude, candidate["longitude"], candidate["latitude"])
        skill_score = 1.0 if _skill_match(category, candidate["skills"]) else 0.55
        load_score = 1 - candidate["current_load"] / candidate["max_load"]
        distance_score = max(0.0, 1 - distance / 20)
        score = skill_score * 0.45 + load_score * 0.25 + distance_score * 0.2 + candidate["rating"] / 100 * 0.1
        ranked.append(
            RankedWorker(
                user_id=int(candidate["user_id"]),
                display_name=str(candidate["display_name"]),
                score=round(score, 3),
                distance_km=round(distance, 2),
                decision_factors={
                    "skill": round(skill_score, 3),
                    "load": round(load_score, 3),
                    "distance": round(distance_score, 3),
                },
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:limit]
