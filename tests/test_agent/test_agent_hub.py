import pytest

from src.agent.engine import AgentEngine
from src.agent.hub import AgentHub, decision_agents
from src.agent.policies.arbitration import ArbitrationPolicy
from src.agent.work_order_agent import WorkOrderAgent


@pytest.mark.asyncio
async def test_hub_registers_work_order_agent():
    hub = AgentHub()
    for agent in decision_agents().values():
        hub.register(agent)
    assert hub.names == ["work-order-agent"]
    hub.unregister("work-order-agent")
    assert hub.names == []


@pytest.mark.asyncio
async def test_hub_keeps_higher_confidence_category():
    hub = AgentHub([WorkOrderAgent()])
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
async def test_engine_runs_work_order_agent_for_intent():
    engine = AgentEngine.with_builtins()
    assert "work-order-agent" in engine.state_center.names
    state, results = await engine.run(
        "t-engine",
        {"normalized_text": "空调不制冷", "area": "西区", "phase": "create"},
        names=["work-order-agent"],
    )
    assert results[0].success
    assert state["category"] == "暖通空调"
    assert state.get("steps") == ["intent"]


def test_arbitration_safety_override():
    verdict = ArbitrationPolicy.resolve_intent_conflict(
        key="category",
        held="环境卫生",
        incoming="安全隐患",
        held_confidence=0.95,
        incoming_confidence=0.7,
        held_writer="work-order-agent",
        incoming_writer="work-order-agent",
    )
    assert verdict.value == "安全隐患"
    assert verdict.reason == "safety_override"
