from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent


class CreditAgent(BaseAgent):
    """Backward-compatible shim — prefer src.agent.tools.credit."""

    name = "credit-agent"

    async def run(self, state: dict[str, Any]) -> AgentResult:
        from src.agent.tools.credit import compute_credit_delta

        result = compute_credit_delta(
            status=str(state.get("status")),
            rating=state.get("rating"),
            sla_deadline=state.get("sla_deadline"),
            completed_at=state.get("completed_at"),
        )
        return AgentResult(
            agent=self.name,
            success=True,
            output={"credit_delta": result.delta, "credit_reason": result.reason, "on_time": result.on_time},
        )
