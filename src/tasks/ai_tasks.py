from __future__ import annotations

import asyncio

from src.core.config import settings
from src.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="lingshu.enrich_work_order",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    rate_limit=settings.ai_enrich_rate_limit,
)
def enrich_work_order(self, order_id: int, trace_id: str) -> dict[str, object]:
    from src.service.work_order_service import enrich_work_order_record

    return asyncio.run(enrich_work_order_record(order_id, trace_id))


@celery_app.task(name="lingshu.drain_pending_ai")
def drain_pending_ai(limit: int = 10) -> dict[str, object]:
    return asyncio.run(_drain_pending_ai(limit))


async def _drain_pending_ai(limit: int) -> dict[str, object]:
    from src.dao.work_order_dao import WorkOrderDAO
    from src.extensions.postgres import AsyncSessionLocal
    from src.service.work_order_service import enqueue_ai_enrichment

    async with AsyncSessionLocal() as session:
        order_ids = await WorkOrderDAO(session).list_pending_ai_enrichment(limit)
    queued = 0
    for order_id in order_ids:
        if enqueue_ai_enrichment(order_id, f"drain-{order_id}"):
            queued += 1
    return {"queued": queued, "scanned": len(order_ids)}
