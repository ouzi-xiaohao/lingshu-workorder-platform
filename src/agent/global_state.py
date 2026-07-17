import asyncio
from copy import deepcopy
from typing import Any


class GlobalStateCenter:
    def __init__(self):
        self._states: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def create(self, trace_id: str, initial: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            self._states[trace_id] = {**initial, "history": []}
            return deepcopy(self._states[trace_id])

    async def update(self, trace_id: str, agent: str, output: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            state = self._states.setdefault(trace_id, {"history": []})
            state.update(output)
            state["history"].append({"agent": agent, "output": deepcopy(output)})
            return deepcopy(state)

    async def get(self, trace_id: str) -> dict[str, Any]:
        async with self._lock:
            return deepcopy(self._states.get(trace_id, {}))


global_state = GlobalStateCenter()
