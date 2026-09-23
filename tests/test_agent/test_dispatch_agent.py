import pytest

from src.agent.dispatch_agent import DispatchAgent


@pytest.mark.asyncio
async def test_dispatch_prefers_matching_skill():
    state = {"category": "暖通空调", "longitude": 121.47, "latitude": 31.23, "worker_candidates": [
        {"user_id": 1, "display_name": "甲", "skills": "综合服务", "longitude": 121.47, "latitude": 31.23, "current_load": 0, "max_load": 4, "rating": 99},
        {"user_id": 2, "display_name": "乙", "skills": "暖通空调", "longitude": 121.47, "latitude": 31.23, "current_load": 1, "max_load": 4, "rating": 92},
    ]}
    result = await DispatchAgent().run(state)
    assert result.output["worker_name"] == "乙"
    assert result.output["strategy"] == "balanced-local-skilled"
    assert result.output["decision_trace"]
    assert result.output["decision_factors"]["skill"] == 1.0


@pytest.mark.asyncio
async def test_emergency_dispatch_expands_area_before_using_generalist():
    state = {
        "category": "暖通空调",
        "priority": "紧急",
        "area": "东区",
        "longitude": 121.47,
        "latitude": 31.23,
        "worker_candidates": [
            {"user_id": 1, "display_name": "本区综合员", "area": "东区", "skills": "综合服务", "longitude": 121.47, "latitude": 31.23, "current_load": 0, "max_load": 4, "rating": 98},
            {"user_id": 2, "display_name": "跨区空调员", "area": "西区", "skills": "暖通空调", "longitude": 121.48, "latitude": 31.23, "current_load": 1, "max_load": 4, "rating": 92},
        ],
    }
    result = await DispatchAgent().run(state)
    assert result.success
    assert result.output["worker_name"] == "跨区空调员"
    assert result.output["strategy"] == "emergency-cross-area-skilled"
    assert len(result.output["decision_trace"]) == 3


@pytest.mark.asyncio
async def test_safety_order_escalates_when_no_qualified_worker():
    state = {
        "category": "安全隐患",
        "priority": "紧急",
        "area": "东区",
        "worker_candidates": [
            {"user_id": 1, "display_name": "综合员", "area": "东区", "skills": "综合服务", "longitude": 121.47, "latitude": 31.23, "current_load": 0, "max_load": 4, "rating": 98},
        ],
    }
    result = await DispatchAgent().run(state)
    assert not result.success
    assert result.output["requires_human_review"] is True
    assert "人工调度" in result.message
