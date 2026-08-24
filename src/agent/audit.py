from __future__ import annotations

import json
from typing import Any

from src.core.config import settings
from src.models.work_order import WorkOrderEvent


def needs_human_review(state: dict[str, Any]) -> bool:
    if state.get("_human_review"):
        return True
    confidence = float(state.get("confidence") or 0)
    return confidence < settings.intent_human_review_threshold


def build_intent_audit_payload(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "category": state.get("category"),
        "priority": state.get("priority"),
        "confidence": state.get("confidence"),
        "intent_source": state.get("intent_source"),
        "rationale": state.get("rationale"),
        "tags": state.get("tags"),
        "evidence_count": state.get("evidence_count"),
        "media_types": state.get("media_types"),
        "steps": state.get("steps"),
        "phase": state.get("phase"),
    }


def build_dispatch_audit_payload(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "worker_id": state.get("worker_id"),
        "worker_name": state.get("worker_name"),
        "dispatch_score": state.get("dispatch_score"),
        "distance_km": state.get("distance_km"),
        "decision_factors": state.get("decision_factors"),
        "top_candidates": state.get("top_candidates"),
        "steps": state.get("steps"),
    }


def events_from_agent_state(
    work_order_id: int,
    trace_id: str,
    state: dict[str, Any],
    *,
    actor_type: str = "system",
    to_status: str | None = None,
) -> list[WorkOrderEvent]:
    events: list[WorkOrderEvent] = []
    intent_payload = build_intent_audit_payload(state)
    if intent_payload.get("category"):
        events.append(
            WorkOrderEvent(
                work_order_id=work_order_id,
                actor_type=actor_type,
                action="ai_decision",
                to_status=to_status,
                detail=json.dumps({"kind": "intent", **intent_payload}, ensure_ascii=False),
                trace_id=trace_id,
            )
        )

    for item in state.get("_arbitration", []):
        events.append(
            WorkOrderEvent(
                work_order_id=work_order_id,
                actor_type="arbitration-policy",
                action="ai_conflict",
                to_status=to_status,
                detail=json.dumps(item, ensure_ascii=False),
                trace_id=trace_id,
            )
        )

    if needs_human_review(state):
        review_items = state.get("_human_review") or []
        events.append(
            WorkOrderEvent(
                work_order_id=work_order_id,
                actor_type="arbitration-policy",
                action="needs_human_review",
                to_status=to_status or "待人审",
                detail=json.dumps(
                    {
                        "confidence": state.get("confidence"),
                        "category": state.get("category"),
                        "priority": state.get("priority"),
                        "conflicts": review_items,
                    },
                    ensure_ascii=False,
                ),
                trace_id=trace_id,
            )
        )
    return events


def dispatch_decision_event(
    work_order_id: int,
    trace_id: str,
    state: dict[str, Any],
    *,
    from_status: str | None = None,
) -> WorkOrderEvent:
    return WorkOrderEvent(
        work_order_id=work_order_id,
        actor_type="work-order-agent",
        action="ai_dispatch_decision",
        from_status=from_status,
        to_status="已派单",
        detail=json.dumps(build_dispatch_audit_payload(state), ensure_ascii=False),
        trace_id=trace_id,
    )
