from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.common.circuit_breaker import CircuitState, circuits
from src.core.config import settings


@dataclass
class AgentHealthReport:
    alerts: list[str] = field(default_factory=list)
    checks: dict[str, str] = field(default_factory=dict)

    @property
    def healthy(self) -> bool:
        return not self.alerts


class AgentWatchdog:
    """Operational probe for agent availability — not part of the decision pipeline."""

    AGENT_CIRCUITS = ("ai-llm", "ai-llm-backup", "ai-stt", "ai-vision")

    def inspect(self) -> AgentHealthReport:
        report = AgentHealthReport()
        for name in self.AGENT_CIRCUITS:
            state = circuits.get(name).state
            report.checks[name] = str(state)
            if state is CircuitState.OPEN:
                report.alerts.append(f"依赖 {name} 熔断中")
        if settings.ai_mode in {"local", "production"} and not settings.llm_api_url:
            report.alerts.append("AI 模式已启用但未配置 LLM_API_URL")
        return report


watchdog = AgentWatchdog()
