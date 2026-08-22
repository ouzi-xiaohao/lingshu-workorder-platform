import pytest

from src.agent.engine import AgentEngine
from src.agent.hub import AgentHub, builtin_agents
from src.agent.intent_agent import IntentAgent


@pytest.mark.asyncio
async def test_hub_registers_and_unregisters_builtin_agents():
    hub = AgentHub()
    for agent in builtin_agents().values():
        hub.register(agent)
    assert {"intent-agent", "dispatch-agent", "order-flow-agent", "credit-agent", "patrol-agent"} <= set(hub.names)
    hub.unregister("patrol-agent")
    assert "patrol-agent" not in hub.names


@pytest.mark.asyncio
async def test_hub_keeps_higher_confidence_category():
    hub = AgentHub([IntentAgent()])
    kept, _ = await hub.execute("t-keep", {
        "normalized_text": "空调不制冷",
        "area": "西区",
        "category": "综合服务",
        "confidence": 0.99,
    })
    assert kept["category"] == "综合服务"
    assert kept["_arbitration"]

    replaced, _ = await hub.execute("t-replace", {
        "normalized_text": "空调不制冷",
        "area": "西区",
        "category": "综合服务",
        "confidence": 0.4,
    })
    assert replaced["category"] == "暖通空调"


@pytest.mark.asyncio
async def test_engine_runs_plugged_subset():
    engine = AgentEngine.with_builtins()
    assert "intent-agent" in engine.state_center.names
    engine.unplug("patrol-agent")
    assert "patrol-agent" not in engine.state_center.names
    state, results = await engine.run("t-engine", {"normalized_text": "空调不制冷", "area": "西区"}, names=["intent-agent"])
    assert results[0].success
    assert state["category"] == "暖通空调"
