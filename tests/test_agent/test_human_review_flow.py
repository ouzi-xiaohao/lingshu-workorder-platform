import pytest

from src.agent.tools.order_flow import validate_transition


def test_human_review_status_transitions():
    assert validate_transition("待人审", "待派单").ok
    assert not validate_transition("待人审", "已派单").ok
    assert validate_transition("待派单", "待人审").ok
