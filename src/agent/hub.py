from __future__ import annotations

from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent
from src.agent.policies.arbitration import ArbitrationPolicy, DISPATCH_OWNED_KEYS, INTENT_OWNED_KEYS
from src.agent.work_order_agent import WorkOrderAgent
from src.common.tracing import traced


def decision_agents() -> dict[str, BaseAgent]:
    agents = [WorkOrderAgent()]
    return {agent.name: agent for agent in agents}


class AgentHub:
    """Shared-state pipeline for the work-order decision agent with deterministic arbitration."""

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
        state: dict[str, Any] = {
            "trace_id": trace_id,
            "_arbitration": [],
            "_writers": {},
            **initial_state,
        }
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
        top_candidates = set(result.output.get("top_candidates") or [])

        for key, value in result.output.items():
            if key in {"steps", "top_candidates", "phase"}:
                if key == "steps":
                    state[key] = value
                elif key == "top_candidates":
                    state[key] = value
                continue

            if key in DISPATCH_OWNED_KEYS:
                if key in state and state[key] != value and top_candidates:
                    try:
                        ArbitrationPolicy.guard_dispatch_output({key: value, "worker_id": result.output.get("worker_id", 0)}, top_candidates)
                    except ValueError:
                        state["_arbitration"].append({
                            "key": key,
                            "kept": state[key],
                            "rejected": value,
                            "winner": state["_writers"].get(key),
                            "loser": result.agent,
                            "reason": "dispatch_outside_top_k",
                        })
                        continue
                state[key] = value
                state["_writers"][key] = result.agent
                continue

            if key in INTENT_OWNED_KEYS and key in state and state[key] != value:
                verdict = ArbitrationPolicy.resolve_intent_conflict(
                    key=key,
                    held=state[key],
                    incoming=value,
                    held_confidence=held_confidence,
                    incoming_confidence=incoming_confidence,
                    held_writer=state["_writers"].get(key),
                    incoming_writer=result.agent,
                )
                if verdict.needs_human:
                    state.setdefault("_human_review", []).append({"key": key, "held": state[key], "incoming": value})
                if verdict.winner != result.agent:
                    state["_arbitration"].append({
                        "key": key,
                        "kept": verdict.value,
                        "rejected": value,
                        "winner": verdict.winner,
                        "loser": result.agent,
                        "reason": verdict.reason,
                    })
                    continue
                state[key] = verdict.value
                state["_writers"][key] = verdict.winner or result.agent
                continue

            state[key] = value
            if key in INTENT_OWNED_KEYS | DISPATCH_OWNED_KEYS:
                state["_writers"][key] = result.agent

        if result.output.get("confidence") is not None:
            state["confidence"] = incoming_confidence
