from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent
from src.agent.global_state import global_state
from src.common.redis_tools import coordination


class AgentScheduler:
    def __init__(self, agents: list[BaseAgent]):
        self.agents = agents

    async def execute(self, trace_id: str, initial_state: dict[str, Any]) -> tuple[dict[str, Any], list[AgentResult]]:
        await global_state.create(trace_id, initial_state)
        results: list[AgentResult] = []
        async with coordination.lock(f"agent-scheduler:{trace_id}"):
            for agent in self.agents:
                state = await global_state.get(trace_id)
                result = await agent.run(state)
                results.append(result)
                if not result.success:
                    break
                await global_state.update(trace_id, agent.name, result.output)
        return await global_state.get(trace_id), results
