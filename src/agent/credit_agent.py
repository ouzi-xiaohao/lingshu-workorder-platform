from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent


class CreditAgent(BaseAgent):
    name = "credit-agent"

    async def run(self, state: dict[str, Any]) -> AgentResult:
        if state.get("status") != "已完成":
            return AgentResult(agent=self.name, success=True, output={"credit_delta": 0})
        rating = float(state.get("rating") or 5)
        on_time = bool(state.get("on_time", True))
        delta = 10 + (5 if on_time else -3) + (3 if rating >= 4.5 else 0)
        return AgentResult(agent=self.name, success=True, output={"credit_delta": delta, "credit_reason": "工单完成积分结算"})
