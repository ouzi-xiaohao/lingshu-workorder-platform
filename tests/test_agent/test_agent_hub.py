import pytest

from src.agent.engine import AgentEngine
from src.agent.hub import AgentHub, decision_agents
from src.agent.intent_agent import IntentAgent
from src.agent.policies.arbitration import ArbitrationPolicy


@pytest.mark.asyncio
async def test_hub_registers_decision_agents():
    hub = AgentHub()
    for agent in decision_agents().values():
        hub.register(agent)
    assert {"coordinator-agent", "intent-agent", "dispatch-agent"} <= set(hub.names)
    hub.unregister("dispatch-agent")
    assert "dispatch-agent" not in hub.names


@pytest.mark.asyncio
async def test_hub_keeps_higher_confidence_category():
    hub = AgentHub([IntentAgent()])
    kept, _ = await hub.execute("t-keep", {
        "normalized_text": "空调不制冷",
        "area": "西区",
        "category": "综合服务",
        "confidence": 0.99,
        "phase": "create",
    })
    assert kept["category"] == "综合服务"
    assert kept["_arbitration"]

    replaced, _ = await hub.execute("t-replace", {
        "normalized_text": "空调不制冷",
        "area": "西区",
        "category": "综合服务",
        "confidence": 0.4,
        "phase": "create",
    })
    assert replaced["category"] == "暖通空调"


@pytest.mark.asyncio
async def test_engine_runs_coordinator_for_intent():
    engine = AgentEngine.with_builtins()
    assert "coordinator-agent" in engine.state_center.names
    state, results = await engine.run(
        "t-engine",
        {"normalized_text": "空调不制冷", "area": "西区", "phase": "create"},
        names=["coordinator-agent"],
    )
    assert results[0].success
    assert state["category"] == "暖通空调"
    assert "intent-agent" in state.get("steps", [])


def test_arbitration_safety_override():
    verdict = ArbitrationPolicy.resolve_intent_conflict(
        key="category",
        held="环境卫生",
        incoming="安全隐患",
        held_confidence=0.95,
        incoming_confidence=0.7,
        held_writer="intent-agent",
        incoming_writer="intent-agent",
    )
    assert verdict.value == "安全隐患"
    assert verdict.reason == "safety_override"
