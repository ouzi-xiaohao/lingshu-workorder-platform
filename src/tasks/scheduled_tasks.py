import asyncio

from src.dao.patrol_dao import PatrolDAO
from src.dao.system_dao import SystemDAO
from src.extensions.postgres import AsyncSessionLocal
from src.service.patrol_service import evaluate_patrol_metrics
from src.tasks.celery_app import celery_app


async def _persist_patrol_report(report: object) -> dict[str, object]:
    async with AsyncSessionLocal() as session:
        system = SystemDAO(session)
        payload = {
            "alerts": report.alerts,
            "backlog_count": report.backlog_count,
            "worker_utilization": report.worker_utilization,
            "hotspot_count": report.hotspot_count,
            "agent_checks": report.agent_checks,
        }
        await system.set_json("patrol:last_report", payload, description="最近一次业务巡检结果")
        if report.alerts:
            await system.set_json("patrol:open_alerts", report.alerts, description="当前未关闭巡检告警")
        else:
            await system.set_json("patrol:open_alerts", [], description="当前未关闭巡检告警")
        await session.commit()
    return payload


async def _run_patrol() -> dict[str, object]:
    async with AsyncSessionLocal() as session:
        dao = PatrolDAO(session)
        report = evaluate_patrol_metrics(
            backlog_count=await dao.count_backlog(),
            worker_utilization=await dao.worker_utilization(),
            hotspot_count=await dao.count_hotspot_areas(),
        )
    payload = await _persist_patrol_report(report)
    return {"status": "patrol-completed", **payload}


async def _run_watchdog() -> dict[str, object]:
    from src.agent.watchdog import watchdog

    report = watchdog.inspect()
    payload = {
        "healthy": report.healthy,
        "checks": report.checks,
        "alerts": report.alerts,
        "llm_degraded": not report.healthy,
    }
    async with AsyncSessionLocal() as session:
        system = SystemDAO(session)
        await system.set_json("agent:health_snapshot", payload, description="Agent 可用性快照")
        await system.set_json("agent:llm_degraded", {"active": payload["llm_degraded"]}, description="LLM 降级开关")
        await session.commit()
    return {"status": "watchdog-completed", **payload}


@celery_app.task
def patrol_system() -> dict[str, object]:
    return asyncio.run(_run_patrol())


@celery_app.task
def agent_watchdog() -> dict[str, object]:
    return asyncio.run(_run_watchdog())


@celery_app.task
def daily_settlement() -> dict[str, object]:
    return {"status": "daily-settlement-completed"}
