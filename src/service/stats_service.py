from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.cache import STATS_KEY, cache
from src.models.work_order import WorkOrder


class StatsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def overview(self) -> dict[str, object]:
        return await cache.get_or_set(STATS_KEY, self._load_overview)

    async def _load_overview(self) -> dict[str, object]:
        since = datetime.now(timezone.utc) - timedelta(days=1)
        result = (await self.session.execute(select(
            func.count(WorkOrder.id).label("total"),
            func.sum(case((WorkOrder.status.in_(["已派单", "已接单", "处理中"]), 1), else_=0)).label("processing"),
            func.sum(case((WorkOrder.status == "已完成", 1), else_=0)).label("completed"),
            func.sum(case((WorkOrder.priority == "紧急", 1), else_=0)).label("urgent"),
        ).where(WorkOrder.created_at >= since))).one()
        return {"today_total": result.total or 0, "processing": int(result.processing or 0), "completed": int(result.completed or 0), "urgent": int(result.urgent or 0)}
