from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import db_session, require_roles
from src.common.cache import WORKER_PERF_PREFIX, cache
from src.dao.worker_dao import WorkerDAO
from src.models.user import User


router = APIRouter()


@router.get("/performance")
async def performance(worker: User = Depends(require_roles("worker", "admin")), session: AsyncSession = Depends(db_session)):
    async def load():
        profile = await WorkerDAO(session).get_by_user_id(worker.id)
        return {"worker": worker.display_name, "credit_balance": worker.credit_balance, "current_load": profile.current_load if profile else 0, "max_load": profile.max_load if profile else 0, "rating": profile.rating if profile else 0}
    return {"code": "OK", "data": await cache.get_or_set(f"{WORKER_PERF_PREFIX}{worker.id}", load, ttl=15)}
