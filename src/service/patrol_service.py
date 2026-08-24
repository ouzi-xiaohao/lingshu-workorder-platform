from __future__ import annotations

from dataclasses import dataclass, field

from src.agent.watchdog import watchdog
from src.core.config import settings


@dataclass
class PatrolReport:
    alerts: list[str] = field(default_factory=list)
    backlog_count: int = 0
    worker_utilization: float = 0.0
    hotspot_count: int = 0
    agent_checks: dict[str, str] = field(default_factory=dict)


def evaluate_patrol_metrics(
    *,
    backlog_count: int,
    worker_utilization: float,
    hotspot_count: int,
) -> PatrolReport:
    report = PatrolReport(
        backlog_count=backlog_count,
        worker_utilization=worker_utilization,
        hotspot_count=hotspot_count,
    )
    if backlog_count > settings.patrol_backlog_threshold:
        report.alerts.append("待处理工单积压超过阈值")
    if worker_utilization > settings.patrol_utilization_threshold:
        report.alerts.append("现场人员平均负载过高")
    if hotspot_count > 0:
        report.alerts.append("检测到高频问题区域")
    health = watchdog.inspect()
    report.agent_checks = health.checks
    report.alerts.extend(health.alerts)
    return report
