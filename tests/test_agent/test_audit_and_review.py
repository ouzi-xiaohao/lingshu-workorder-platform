import json

import pytest

from src.agent.audit import events_from_agent_state, needs_human_review
from src.agent.intent_rules import classify_intent_rules
from src.ai_services.multimodal_fusion import MultimodalFusionService


def test_needs_human_review_when_low_confidence():
    assert needs_human_review({"confidence": 0.5}) is True
    assert needs_human_review({"confidence": 0.9}) is False


def test_audit_events_include_decision_and_conflict():
    state = {
        "category": "暖通空调",
        "priority": "高",
        "confidence": 0.91,
        "intent_source": "rules",
        "rationale": "test",
        "tags": ["暖通空调", "高", "西区"],
        "_arbitration": [{"key": "category", "kept": "综合服务", "rejected": "暖通空调", "reason": "higher_confidence"}],
    }
    events = events_from_agent_state(1, "trace-1", state, to_status="待派单")
    actions = {event.action for event in events}
    assert "ai_decision" in actions
    assert "ai_conflict" in actions
    payload = json.loads(next(event.detail for event in events if event.action == "ai_decision"))
    assert payload["kind"] == "intent"
    assert payload["category"] == "暖通空调"


def test_rules_use_visual_evidence_for_smoke():
    result = classify_intent_rules("路灯闪烁", area="西区", evidence=["视觉标签：smoke"])
    assert result["category"] == "安全隐患"


@pytest.mark.asyncio
async def test_fusion_returns_evidence_list():
    fused = await MultimodalFusionService().fuse("路灯损坏", "B2区路灯不亮", [], heavy=False)
    assert fused["evidence"]
    assert any("路灯" in item for item in fused["evidence"])
