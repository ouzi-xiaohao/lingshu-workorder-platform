from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent
from src.agent.dispatch_tools import BALANCED_WEIGHTS, EMERGENCY_WEIGHTS, DispatchPolicy, DispatchToolkit


class DispatchAgent(BaseAgent):
    name = "dispatch-agent"

    def __init__(self, toolkit: DispatchToolkit | None = None):
        self.tools = toolkit or DispatchToolkit()

    async def run(self, state: dict[str, Any]) -> AgentResult:
        candidates: list[dict[str, Any]] = state.get("worker_candidates", [])
        if not candidates:
            return AgentResult(agent=self.name, success=False, message="暂无可调度人员")

        category = str(state.get("category", "综合服务"))
        priority = str(state.get("priority", "中"))
        area = str(state.get("area", "全园区"))
        longitude = float(state.get("longitude", 0))
        latitude = float(state.get("latitude", 0))
        policies = self._plan(priority, category)
        decision_trace: list[dict[str, Any]] = []
        ranked: list[dict[str, Any]] = []
        selected_policy: DispatchPolicy | None = None

        # Observe -> plan -> call tools -> evaluate -> retry with a safer fallback.
        for step, policy in enumerate(policies, start=1):
            eligible = self.tools.filter_candidates(
                candidates,
                category=category,
                area=area,
                policy=policy,
            )
            decision_trace.append({
                "step": step,
                "action": "filter_candidates",
                "policy": policy.name,
                "eligible_count": len(eligible),
            })
            if not eligible:
                continue
            ranked = self.tools.rank_candidates(
                eligible,
                category=category,
                longitude=longitude,
                latitude=latitude,
                weights=policy.weights,
            )
            decision_trace.append({
                "step": step,
                "action": "rank_candidates",
                "policy": policy.name,
                "top_score": ranked[0]["score"],
            })
            selected_policy = policy
            break

        if not ranked or selected_policy is None:
            return AgentResult(
                agent=self.name,
                success=False,
                output={"decision_trace": decision_trace, "requires_human_review": True},
                message="没有满足安全约束的候选人，需人工调度",
            )

        winner = ranked[0]
        worker = winner["candidate"]
        runner_up_score = float(ranked[1]["score"]) if len(ranked) > 1 else 0.0
        margin = float(winner["score"]) - runner_up_score
        confidence = min(0.99, 0.72 + max(0.0, margin) * 0.8 + (0.08 if winner["factors"]["skill"] == 1 else 0))
        requires_human_review = category == "安全隐患" and selected_policy.allow_generalist
        return AgentResult(agent=self.name, success=True, output={
            "worker_id": worker["user_id"],
            "worker_name": worker["display_name"],
            "dispatch_score": winner["score"],
            "distance_km": winner["distance_km"],
            "decision_factors": winner["factors"],
            "strategy": selected_policy.name,
            "weights": selected_policy.weights,
            "confidence": round(confidence, 3),
            "requires_human_review": requires_human_review,
            "decision_trace": decision_trace,
            "alternatives": [
                {"worker_id": item["candidate"]["user_id"], "score": item["score"]}
                for item in ranked[1:3]
            ],
        })

    def _plan(self, priority: str, category: str) -> list[DispatchPolicy]:
        if priority == "紧急":
            policies = [
                DispatchPolicy("emergency-local-skilled", EMERGENCY_WEIGHTS),
                DispatchPolicy("emergency-cross-area-skilled", EMERGENCY_WEIGHTS, local_only=False),
            ]
            if category != "安全隐患":
                policies.append(DispatchPolicy(
                    "emergency-local-generalist",
                    EMERGENCY_WEIGHTS,
                    allow_generalist=True,
                ))
            return policies
        return [
            DispatchPolicy("balanced-local-skilled", BALANCED_WEIGHTS),
            DispatchPolicy("balanced-local-generalist", BALANCED_WEIGHTS, allow_generalist=True),
            DispatchPolicy("balanced-cross-area-skilled", BALANCED_WEIGHTS, local_only=False),
        ]
