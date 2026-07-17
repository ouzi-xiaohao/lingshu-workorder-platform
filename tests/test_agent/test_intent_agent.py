import pytest

from src.agent.intent_agent import IntentAgent


@pytest.mark.asyncio
async def test_intent_agent_classifies_air_conditioner():
    result = await IntentAgent().run({"normalized_text": "B2 办公区空调无法制冷", "area": "西区"})
    assert result.success
    assert result.output["category"] == "暖通空调"
    assert result.output["priority"] == "高"
