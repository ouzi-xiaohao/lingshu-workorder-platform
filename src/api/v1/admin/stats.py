from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import db_session, require_roles
from src.models.user import User
from src.service.stats_service import StatsService


router = APIRouter()


@router.get("/overview")
async def overview(_: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    return {"code": "OK", "data": await StatsService(session).overview()}
