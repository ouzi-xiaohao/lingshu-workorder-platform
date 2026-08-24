import pytest

from src.agent.work_order_agent import WorkOrderAgent


@pytest.mark.asyncio
async def test_intent_phase_classifies_hvac():
    result = await WorkOrderAgent().run({"normalized_text": "B2 办公区空调无法制冷", "area": "西区", "phase": "create"})
    assert result.success
    assert result.output["category"] == "暖通空调"
    assert result.output["steps"] == ["intent"]


@pytest.mark.asyncio
async def test_dispatch_phase_selects_worker():
    state = {
        "phase": "dispatch",
        "category": "暖通空调",
        "longitude": 0,
        "latitude": 0,
        "worker_candidates": [
            {
                "user_id": 2,
                "display_name": "张师傅",
                "skills": "暖通空调",
                "longitude": 0.01,
                "latitude": 0.01,
                "current_load": 1,
                "max_load": 5,
                "rating": 95,
            },
            {
                "user_id": 3,
                "display_name": "李师傅",
                "skills": "综合服务",
                "longitude": 0.5,
                "latitude": 0.5,
                "current_load": 0,
                "max_load": 5,
                "rating": 80,
            },
        ],
    }
    result = await WorkOrderAgent().run(state)
    assert result.success
    assert result.output["worker_id"] == 2
    assert result.output["steps"] == ["dispatch"]
