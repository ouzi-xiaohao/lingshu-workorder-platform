"""Deprecated: business patrol moved to src.service.patrol_service and Celery tasks."""

from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent


class PatrolAgent(BaseAgent):
    name = "patrol-agent"

    async def run(self, state: dict[str, Any]) -> AgentResult:
        raise RuntimeError("PatrolAgent 已下线，请使用 patrol_service / scheduled_tasks.patrol_system")
