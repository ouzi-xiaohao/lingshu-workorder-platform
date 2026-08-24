from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent
from src.agent.dispatch_agent import DispatchAgent
from src.agent.intent_agent import IntentAgent
from src.ai_services.llm_client import llm_client
from src.common.tracing import traced


class CoordinatorAgent(BaseAgent):
    """LLM-planned orchestrator with rule fallback; does not own business fields."""

    name = "coordinator-agent"

    def __init__(self) -> None:
        self._intent = IntentAgent()
        self._dispatch = DispatchAgent()

    async def run(self, state: dict[str, Any]) -> AgentResult:
        plan = await llm_client.plan_coordinator(state)
        tool = str(plan.get("tool") or "intent")
        steps: list[str] = [f"coordinator:{plan.get('coordinator_source', 'rules')}"]

        if tool == "intent":
            async with traced("agent.intent-agent", agent="intent-agent"):
                intent = await self._intent.run(state)
            steps.append("intent-agent")
            if not intent.success:
                return AgentResult(agent=self.name, success=False, message=intent.message, output={"steps": steps, **plan})
            return AgentResult(
                agent=self.name,
                success=True,
                output={
                    "steps": steps,
                    "coordinator_tool": tool,
                    "coordinator_rationale": plan.get("rationale"),
                    "coordinator_source": plan.get("coordinator_source"),
                    **intent.output,
                },
                message="intent completed",
            )

        if tool == "dispatch":
            async with traced("agent.dispatch-agent", agent="dispatch-agent"):
                dispatch = await self._dispatch.run(state)
            steps.append("dispatch-agent")
            if not dispatch.success:
                return AgentResult(agent=self.name, success=False, message=dispatch.message, output={"steps": steps, **plan})
            return AgentResult(
                agent=self.name,
                success=True,
                output={
                    "steps": steps,
                    "coordinator_tool": tool,
                    "coordinator_rationale": plan.get("rationale"),
                    "coordinator_source": plan.get("coordinator_source"),
                    **dispatch.output,
                },
                message="dispatch completed",
            )

        return AgentResult(agent=self.name, success=False, message=f"unsupported coordinator tool: {tool}")
