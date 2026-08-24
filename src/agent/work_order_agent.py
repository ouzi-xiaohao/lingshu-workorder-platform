from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent
from src.agent.intent_rules import classify_intent_rules
from src.agent.tools.dispatch_scoring import rank_worker_candidates
from src.ai_services.llm_client import llm_client
from src.common.tracing import traced


class WorkOrderAgent(BaseAgent):
    """Single decision agent: intent recognition and dispatch by business phase."""

    name = "work-order-agent"

    async def run(self, state: dict[str, Any]) -> AgentResult:
        phase = str(state.get("phase") or "create")

        if phase in {"create", "enrich"}:
            async with traced("agent.work-order-agent.intent", phase=phase):
                output = await self._run_intent(state)
            return AgentResult(
                agent=self.name,
                success=True,
                output={**output, "steps": ["intent"], "phase": phase},
                message="intent completed",
            )

        if phase == "dispatch":
            async with traced("agent.work-order-agent.dispatch", phase=phase):
                output, message = self._run_dispatch(state)
            if output is None:
                return AgentResult(agent=self.name, success=False, message=message)
            return AgentResult(
                agent=self.name,
                success=True,
                output={**output, "steps": ["dispatch"], "phase": phase},
                message="dispatch completed",
            )

        return AgentResult(agent=self.name, success=False, message=f"unsupported phase: {phase}")

    async def _run_intent(self, state: dict[str, Any]) -> dict[str, Any]:
        text = str(state.get("normalized_text", ""))
        area = str(state.get("area", "未知区域"))
        evidence = list(state.get("evidence") or [])
        try:
            return await llm_client.classify_intent(text, area=area, evidence=evidence)
        except Exception:
            return classify_intent_rules(text, area=area, evidence=evidence)

    def _run_dispatch(self, state: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        candidates = state.get("worker_candidates", [])
        if not candidates:
            return None, "暂无可调度人员"
        ranked = rank_worker_candidates(
            category=str(state.get("category", "综合服务")),
            longitude=float(state.get("longitude", 0)),
            latitude=float(state.get("latitude", 0)),
            candidates=candidates,
        )
        if not ranked:
            return None, "候选人员均已满载"
        worker = ranked[0]
        return {
            "worker_id": worker.user_id,
            "worker_name": worker.display_name,
            "dispatch_score": worker.score,
            "distance_km": worker.distance_km,
            "decision_factors": worker.decision_factors,
            "top_candidates": [item.user_id for item in ranked],
        }, ""
