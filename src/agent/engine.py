from __future__ import annotations

from typing import Any

from src.agent.base_agent import BaseAgent
from src.agent.hub import AgentHub, decision_agents
from src.core.config import settings


class AgentEngine:
    """Runs decision agents against a shared AgentHub."""

    _shared: "AgentEngine | None" = None

    def __init__(self, state_center: AgentHub | None = None):
        self.state_center = state_center or AgentHub()

    @classmethod
    def shared(cls) -> "AgentEngine":
        if cls._shared is None:
            cls._shared = cls.with_builtins()
        return cls._shared

    @classmethod
    def with_builtins(cls) -> "AgentEngine":
        engine = cls()
        catalog = decision_agents()
        for name in (item.strip() for item in settings.agent_pipeline.split(",")):
            agent = catalog.get(name)
            if agent:
                engine.plug(agent)
        return engine

    def plug(self, agent: BaseAgent) -> "AgentEngine":
        self.state_center.register(agent)
        return self

    def unplug(self, name: str) -> "AgentEngine":
        self.state_center.unregister(name)
        return self

    async def run(self, trace_id: str, initial_state: dict[str, Any], names: list[str] | None = None):
        return await self.state_center.execute(trace_id, initial_state, names)
