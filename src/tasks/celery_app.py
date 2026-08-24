from celery import Celery

from src.core.config import settings


celery_app = Celery(
    "lingshu",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
    include=["src.tasks.scheduled_tasks", "src.tasks.ai_tasks"],
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=10,
    task_default_delivery_mode=2,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "patrol-every-5-minutes": {"task": "src.tasks.scheduled_tasks.patrol_system", "schedule": 300.0},
        "agent-watchdog-every-5-minutes": {"task": "src.tasks.scheduled_tasks.agent_watchdog", "schedule": 300.0},
        "daily-credit-settlement": {"task": "src.tasks.scheduled_tasks.daily_settlement", "schedule": 86400.0},
        "drain-ai-every-2-minutes": {"task": "lingshu.drain_pending_ai", "schedule": 120.0},
    },
)
