from src.tasks.celery_app import celery_app


@celery_app.task
def check_sla(work_order_id: int) -> dict[str, object]:
    return {"work_order_id": work_order_id, "action": "sla-checked"}


@celery_app.task
def schedule_callback(work_order_id: int) -> dict[str, object]:
    return {"work_order_id": work_order_id, "action": "callback-scheduled"}
