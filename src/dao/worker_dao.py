from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.user import WorkerProfile


class WorkerDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_available(self, area: str | None = None) -> list[WorkerProfile]:
        statement = select(WorkerProfile).options(selectinload(WorkerProfile.user)).where(
            WorkerProfile.is_deleted.is_(False),
            WorkerProfile.work_status.in_(["available", "busy"]),
            WorkerProfile.current_load < WorkerProfile.max_load,
        )
        if area:
            statement = statement.where(WorkerProfile.user.has(area=area) | WorkerProfile.user.has(area="全园区"))
        return list((await self.session.scalars(statement)).all())

    async def get_by_user_id(self, user_id: int, for_update: bool = False) -> WorkerProfile | None:
        statement = select(WorkerProfile).where(WorkerProfile.user_id == user_id)
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def adjust_load(self, user_id: int | None, delta: int) -> None:
        if not user_id or delta == 0:
            return
        profile = await self.get_by_user_id(user_id, for_update=True)
        if not profile:
            return
        profile.current_load = max(0, profile.current_load + delta)
        profile.work_status = "busy" if profile.current_load >= profile.max_load else "available"
