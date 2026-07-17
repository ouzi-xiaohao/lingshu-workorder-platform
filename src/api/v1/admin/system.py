from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import db_session, require_roles
from src.models.system import SystemConfig
from src.models.user import User


router = APIRouter()


class ConfigUpdate(BaseModel):
    value: str = Field(max_length=2000)
    description: str = Field(default="", max_length=300)


@router.get("/configs")
async def configs(_: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    items = list((await session.scalars(select(SystemConfig).where(SystemConfig.is_deleted.is_(False)))).all())
    return {"code": "OK", "data": [{"key": item.key, "value": item.value, "description": item.description, "value_type": item.value_type} for item in items]}


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
    return {"code": "OK", "data": {"key": item.key, "value": item.value}}
