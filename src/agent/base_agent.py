from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AgentResult:
    agent: str
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    completed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BaseAgent(ABC):
    name = "base-agent"

    @abstractmethod
    async def run(self, state: dict[str, Any]) -> AgentResult:
        raise NotImplementedError
