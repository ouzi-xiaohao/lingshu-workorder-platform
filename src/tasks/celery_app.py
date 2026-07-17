from celery import Celery

from src.core.config import settings


celery_app = Celery("lingshu", broker=settings.rabbitmq_url, backend=settings.redis_url, include=["src.tasks.ai_tasks", "src.tasks.order_tasks", "src.tasks.scheduled_tasks"])
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=10,
    task_routes={"src.tasks.ai_tasks.*": {"queue": "ai"}, "src.tasks.order_tasks.*": {"queue": "workorder"}},
    beat_schedule={
        "patrol-every-5-minutes": {"task": "src.tasks.scheduled_tasks.patrol_system", "schedule": 300.0},
        "daily-credit-settlement": {"task": "src.tasks.scheduled_tasks.daily_settlement", "schedule": 86400.0},
    },
)
