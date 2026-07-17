from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent
from src.common.geo_calc import haversine_km


class DispatchAgent(BaseAgent):
    name = "dispatch-agent"

    async def run(self, state: dict[str, Any]) -> AgentResult:
        candidates = state.get("worker_candidates", [])
        if not candidates:
            return AgentResult(agent=self.name, success=False, message="暂无可调度人员")
        ranked = []
        category = str(state.get("category", "综合服务"))
        for candidate in candidates:
            if candidate["current_load"] >= candidate["max_load"]:
                continue
            distance = haversine_km(float(state.get("longitude", 0)), float(state.get("latitude", 0)), candidate["longitude"], candidate["latitude"])
            skill_score = 1.0 if category in candidate["skills"] else 0.55
            load_score = 1 - candidate["current_load"] / candidate["max_load"]
            distance_score = max(0.0, 1 - distance / 20)
            score = skill_score * 0.45 + load_score * 0.25 + distance_score * 0.2 + candidate["rating"] / 100 * 0.1
            ranked.append((score, distance, candidate))
        if not ranked:
            return AgentResult(agent=self.name, success=False, message="候选人员均已满载")
        score, distance, worker = max(ranked, key=lambda item: item[0])
        return AgentResult(agent=self.name, success=True, output={
            "worker_id": worker["user_id"],
            "worker_name": worker["display_name"],
            "dispatch_score": round(score, 3),
            "distance_km": round(distance, 2),
            "decision_factors": {"skill": skill_score, "load": round(load_score, 3), "distance": round(distance_score, 3)},
        })
