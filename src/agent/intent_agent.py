from typing import Any

from src.agent.base_agent import AgentResult, BaseAgent
from src.agent.intent_rules import classify_intent_rules
from src.ai_services.llm_client import llm_client


class IntentAgent(BaseAgent):
    name = "intent-agent"

    async def run(self, state: dict[str, Any]) -> AgentResult:
        text = str(state.get("normalized_text", ""))
        area = str(state.get("area", "未知区域"))
        evidence = list(state.get("evidence") or [])
        try:
            output = await llm_client.classify_intent(text, area=area, evidence=evidence)
        except Exception:
            output = classify_intent_rules(text, area=area, evidence=evidence)
        return AgentResult(agent=self.name, success=True, output=output)
