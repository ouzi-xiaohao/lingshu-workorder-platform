from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent
from src.agent.tools.dispatch_scoring import rank_worker_candidates


class DispatchAgent(BaseAgent):
    name = "dispatch-agent"

    async def run(self, state: dict[str, Any]) -> AgentResult:
        candidates = state.get("worker_candidates", [])
        if not candidates:
            return AgentResult(agent=self.name, success=False, message="暂无可调度人员")
        ranked = rank_worker_candidates(
            category=str(state.get("category", "综合服务")),
            longitude=float(state.get("longitude", 0)),
            latitude=float(state.get("latitude", 0)),
            candidates=candidates,
        )
        if not ranked:
            return AgentResult(agent=self.name, success=False, message="候选人员均已满载")
        worker = ranked[0]
        return AgentResult(
            agent=self.name,
            success=True,
            output={
                "worker_id": worker.user_id,
                "worker_name": worker.display_name,
                "dispatch_score": worker.score,
                "distance_km": worker.distance_km,
                "decision_factors": worker.decision_factors,
                "top_candidates": [item.user_id for item in ranked],
            },
        )
