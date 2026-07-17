from src.tasks.celery_app import celery_app


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_multimodal(self, work_order_id: int, trace_id: str) -> dict[str, object]:
    return {"work_order_id": work_order_id, "trace_id": trace_id, "status": "queued-for-ai-worker"}
