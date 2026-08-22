from __future__ import annotations

from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent
from src.agent.credit_agent import CreditAgent
from src.agent.dispatch_agent import DispatchAgent
from src.agent.intent_agent import IntentAgent
from src.agent.order_flow_agent import OrderFlowAgent
from src.agent.patrol_agent import PatrolAgent
from src.common.tracing import traced

_CONFIDENCE_KEYS = {"category", "priority", "tags"}


def builtin_agents() -> dict[str, BaseAgent]:
    agents = [IntentAgent(), DispatchAgent(), OrderFlowAgent(), CreditAgent(), PatrolAgent()]
    return {agent.name: agent for agent in agents}


class AgentHub:
    """Shared-state pipeline: agents read/write one dict, conflicts prefer higher confidence."""

    def __init__(self, agents: list[BaseAgent] | None = None):
        self._registry: dict[str, BaseAgent] = {}
        for agent in agents or []:
            self.register(agent)

    def register(self, agent: BaseAgent) -> None:
        self._registry[agent.name] = agent

    def unregister(self, name: str) -> None:
        self._registry.pop(name, None)

    @property
    def names(self) -> list[str]:
        return list(self._registry)

    async def execute(
        self,
        trace_id: str,
        initial_state: dict[str, Any],
        names: list[str] | None = None,
    ) -> tuple[dict[str, Any], list[AgentResult]]:
        pipeline = names if names is not None else list(self._registry)
        state: dict[str, Any] = {"trace_id": trace_id, "_arbitration": [], **initial_state}
        results: list[AgentResult] = []
        for name in pipeline:
            agent = self._registry.get(name)
            if agent is None:
                raise KeyError(f"agent not registered: {name}")
            async with traced(f"agent.{agent.name}", agent=agent.name):
                result = await agent.run(state)
            results.append(result)
            if not result.success:
                break
            self._merge(state, result)
        return state, results

    def _merge(self, state: dict[str, Any], result: AgentResult) -> None:
        incoming_confidence = float(result.output.get("confidence", state.get("confidence") or 0) or 0)
        held_confidence = float(state.get("confidence") or 0)
        for key, value in result.output.items():
            if (
                key in _CONFIDENCE_KEYS
                and key in state
                and state[key] != value
                and incoming_confidence < held_confidence
            ):
                state["_arbitration"].append({
                    "key": key,
                    "kept": state[key],
                    "rejected": value,
                    "winner": state.get("_writer"),
                    "loser": result.agent,
                    "reason": "higher_confidence",
                })
                continue
            state[key] = value
        if result.output:
            state["_writer"] = result.agent
