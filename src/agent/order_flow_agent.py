from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent


class OrderFlowAgent(BaseAgent):
    """Backward-compatible shim — prefer src.agent.tools.order_flow."""

    name = "order-flow-agent"

    async def run(self, state: dict[str, Any]) -> AgentResult:
        from src.agent.tools.order_flow import validate_transition

        result = validate_transition(str(state.get("current_status")), str(state.get("target_status")))
        if not result.ok:
            return AgentResult(agent=self.name, success=False, message=result.message)
        return AgentResult(
            agent=self.name,
            success=True,
            output={"previous_status": result.previous_status, "status": result.status},
        )
