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
