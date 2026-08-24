from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CreditResult:
    delta: int
    reason: str
    on_time: bool


def compute_credit_delta(
    *,
    status: str,
    rating: float | None = None,
    sla_deadline: datetime | None = None,
    completed_at: datetime | None = None,
) -> CreditResult:
    if status != "已完成":
        return CreditResult(delta=0, reason="工单未完成，不结算", on_time=True)
    score = float(rating or 5)
    on_time = True
    if sla_deadline is not None and completed_at is not None:
        on_time = completed_at <= sla_deadline
    delta = 10 + (5 if on_time else -3) + (3 if score >= 4.5 else 0)
    return CreditResult(delta=delta, reason="工单完成积分结算", on_time=on_time)
