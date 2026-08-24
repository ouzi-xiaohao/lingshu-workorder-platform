from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.user import WorkerProfile
from src.models.work_order import WorkOrder


class PatrolDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_backlog(self) -> int:
        return int(
            await self.session.scalar(
                select(func.count(WorkOrder.id)).where(
                    WorkOrder.is_deleted.is_(False),
                    WorkOrder.status.in_(("待派单", "已派单", "已接单", "处理中", "待回访")),
                )
            )
            or 0
        )

    async def worker_utilization(self) -> float:
        rows = await self.session.scalars(select(WorkerProfile).where(WorkerProfile.is_deleted.is_(False)))
        profiles = list(rows.all())
        if not profiles:
            return 0.0
        total_load = sum(profile.current_load for profile in profiles)
        total_capacity = sum(profile.max_load for profile in profiles)
        return round(total_load / total_capacity, 3) if total_capacity else 0.0

    async def count_hotspot_areas(self) -> int:
        rows = await self.session.execute(
            select(WorkOrder.area, func.count(WorkOrder.id))
            .where(WorkOrder.is_deleted.is_(False), WorkOrder.status != "已取消")
            .group_by(WorkOrder.area)
            .having(func.count(WorkOrder.id) >= settings.patrol_hotspot_threshold)
        )
        return len(rows.all())
