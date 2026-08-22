import asyncio

from src.agent.patrol_agent import PatrolAgent
from src.tasks.celery_app import celery_app


@celery_app.task
def patrol_system() -> dict[str, object]:
    result = asyncio.run(PatrolAgent().run({}))
    return {"status": "patrol-completed", "alerts": result.output.get("alerts", [])}


@celery_app.task
def daily_settlement() -> dict[str, object]:
    return {"status": "daily-settlement-completed"}
