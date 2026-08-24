import pytest

from src.agent.tools.credit import compute_credit_delta
from src.agent.tools.order_flow import validate_transition
from src.agent.watchdog import watchdog
from datetime import datetime, timezone, timedelta


def test_validate_transition_allows_dispatch():
    result = validate_transition("待派单", "已派单")
    assert result.ok
    assert result.status == "已派单"


def test_credit_uses_sla_deadline():
    deadline = datetime.now(timezone.utc) + timedelta(hours=1)
    completed = deadline + timedelta(minutes=30)
    result = compute_credit_delta(status="已完成", rating=5, sla_deadline=deadline, completed_at=completed)
    assert result.delta == 10
    assert result.on_time is False


def test_watchdog_reports_open_circuits():
    from src.common.circuit_breaker import circuits

    breaker = circuits.get("ai-llm")
    breaker.failure_threshold = 1
    breaker.record_failure()
    report = watchdog.inspect()
    assert any("ai-llm" in alert for alert in report.alerts)
