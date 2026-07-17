from src.tasks.celery_app import celery_app


@celery_app.task
def patrol_system() -> dict[str, object]:
    return {"status": "patrol-completed", "alerts": []}


@celery_app.task
def daily_settlement() -> dict[str, object]:
    return {"status": "daily-settlement-completed"}
