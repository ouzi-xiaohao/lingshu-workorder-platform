from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.config import settings


SAFETY_CATEGORIES = {"安全隐患"}
INTENT_OWNED_KEYS = frozenset({"category", "priority", "tags", "confidence"})
DISPATCH_OWNED_KEYS = frozenset({"worker_id", "worker_name", "dispatch_score", "distance_km", "decision_factors"})


@dataclass(frozen=True)
class ArbitrationVerdict:
    winner: str | None
    value: Any
    reason: str
    needs_human: bool = False


class ArbitrationPolicy:
    """Deterministic conflict resolution — not a decision agent."""

    @staticmethod
    def resolve_intent_conflict(
        *,
        key: str,
        held: Any,
        incoming: Any,
        held_confidence: float,
        incoming_confidence: float,
        held_writer: str | None,
        incoming_writer: str,
    ) -> ArbitrationVerdict:
        if key not in INTENT_OWNED_KEYS:
            return ArbitrationVerdict(winner=incoming_writer, value=incoming, reason="non_intent_field")

        if held == incoming:
            return ArbitrationVerdict(winner=incoming_writer, value=incoming, reason="same_value")

        if key == "category" and str(incoming) in SAFETY_CATEGORIES and str(held) not in SAFETY_CATEGORIES:
            return ArbitrationVerdict(winner=incoming_writer, value=incoming, reason="safety_override")

        if key == "category" and str(held) in SAFETY_CATEGORIES and str(incoming) not in SAFETY_CATEGORIES:
            return ArbitrationVerdict(
                winner=held_writer,
                value=held,
                reason="safety_preserved",
            )

        if incoming_confidence < held_confidence:
            return ArbitrationVerdict(winner=held_writer, value=held, reason="higher_confidence")

        if (
            incoming_confidence >= settings.intent_human_review_threshold
            and held_confidence >= settings.intent_human_review_threshold
            and incoming_confidence == held_confidence
            and key in {"category", "priority"}
        ):
            return ArbitrationVerdict(
                winner=held_writer,
                value=held,
                reason="tie_needs_human",
                needs_human=True,
            )

        return ArbitrationVerdict(winner=incoming_writer, value=incoming, reason="incoming_wins")

    @staticmethod
    def guard_dispatch_output(output: dict[str, Any], top_worker_ids: set[int]) -> dict[str, Any]:
        worker_id = int(output.get("worker_id", 0))
        if worker_id and worker_id not in top_worker_ids:
            raise ValueError("dispatch worker outside top candidates")
        return output
