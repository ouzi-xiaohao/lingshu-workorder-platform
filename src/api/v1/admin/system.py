from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import db_session, require_roles
from src.agent.watchdog import watchdog
from src.common.cache import CONFIGS_KEY, cache
from src.common.circuit_breaker import circuits
from src.dao.system_dao import SystemDAO
from src.models.system import SystemConfig
from src.models.user import User


router = APIRouter()


class ConfigUpdate(BaseModel):
    value: str = Field(max_length=2000)
    description: str = Field(default="", max_length=300)


@router.get("/configs")
async def configs(_: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    async def load():
        items = list((await session.scalars(select(SystemConfig).where(SystemConfig.is_deleted.is_(False)))).all())
        return [{"key": item.key, "value": item.value, "description": item.description, "value_type": item.value_type} for item in items]
    return {"code": "OK", "data": await cache.get_or_set(CONFIGS_KEY, load)}


@router.put("/configs/{key}")
async def update_config(key: str, payload: ConfigUpdate, _: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    item = await session.scalar(select(SystemConfig).where(SystemConfig.key == key))
    if item:
        item.value = payload.value
        item.description = payload.description
    else:
        item = SystemConfig(key=key, value=payload.value, description=payload.description)
        session.add(item)
    await session.commit()
    await cache.delete(CONFIGS_KEY)
    return {"code": "OK", "data": {"key": item.key, "value": item.value}}


@router.get("/circuits")
async def circuit_status(_: User = Depends(require_roles("admin"))):
    return {"code": "OK", "data": circuits.snapshot()}


@router.get("/agents")
async def agent_health(_: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    snapshot = await SystemDAO(session).get_json("agent:health_snapshot", {})
    live = watchdog.inspect()
    return {
        "code": "OK",
        "data": {
            "live": {"healthy": live.healthy, "checks": live.checks, "alerts": live.alerts},
            "persisted": snapshot,
            "llm_degraded": await SystemDAO(session).get_json("agent:llm_degraded", {"active": False}),
        },
    }


@router.get("/patrol")
async def patrol_status(_: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    system = SystemDAO(session)
    return {
        "code": "OK",
        "data": {
            "last_report": await system.get_json("patrol:last_report", {}),
            "open_alerts": await system.get_json("patrol:open_alerts", []),
        },
    }
