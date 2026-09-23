from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.geo_calc import haversine_km


@dataclass(frozen=True)
class DispatchPolicy:
    name: str
    weights: dict[str, float]
    require_skill: bool = True
    local_only: bool = True
    allow_generalist: bool = False


BALANCED_WEIGHTS = {"skill": 0.45, "load": 0.25, "distance": 0.20, "rating": 0.10}
EMERGENCY_WEIGHTS = {"skill": 0.45, "load": 0.15, "distance": 0.30, "rating": 0.10}


class DispatchToolkit:
    """Deterministic tools used by the dispatch agent.

    The agent may choose and retry policies, while capacity and scoring stay
    deterministic and auditable.
    """

    @staticmethod
    def filter_candidates(
        candidates: list[dict[str, Any]],
        *,
        category: str,
        area: str,
        policy: DispatchPolicy,
    ) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        for candidate in candidates:
            if int(candidate["current_load"]) >= int(candidate["max_load"]):
                continue
            candidate_area = str(candidate.get("area") or area)
            if policy.local_only and candidate_area not in {area, "全园区"}:
                continue
            exact_skill = category in str(candidate.get("skills", ""))
            generalist = "综合服务" in str(candidate.get("skills", ""))
            if policy.require_skill and not exact_skill:
                if not (policy.allow_generalist and generalist):
                    continue
            selected.append(candidate)
        return selected

    @staticmethod
    def rank_candidates(
        candidates: list[dict[str, Any]],
        *,
        category: str,
        longitude: float,
        latitude: float,
        weights: dict[str, float],
    ) -> list[dict[str, Any]]:
        ranked: list[dict[str, Any]] = []
        for candidate in candidates:
            distance = haversine_km(
                longitude,
                latitude,
                float(candidate["longitude"]),
                float(candidate["latitude"]),
            )
            skills = str(candidate.get("skills", ""))
            skill_score = 1.0 if category in skills else 0.55 if "综合服务" in skills else 0.0
            load_score = 1 - int(candidate["current_load"]) / max(int(candidate["max_load"]), 1)
            distance_score = max(0.0, 1 - distance / 20)
            rating_score = max(0.0, min(float(candidate["rating"]) / 100, 1.0))
            factors = {
                "skill": round(skill_score, 3),
                "load": round(load_score, 3),
                "distance": round(distance_score, 3),
                "rating": round(rating_score, 3),
            }
            score = sum(factors[key] * weights[key] for key in weights)
            ranked.append({
                "candidate": candidate,
                "score": round(score, 3),
                "distance_km": round(distance, 2),
                "factors": factors,
            })
        return sorted(ranked, key=lambda item: item["score"], reverse=True)

