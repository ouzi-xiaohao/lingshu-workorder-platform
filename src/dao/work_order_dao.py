from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.work_order import WorkOrder, WorkOrderEvent


class WorkOrderDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, work_order_id: int, with_relations: bool = True) -> WorkOrder | None:
        statement = select(WorkOrder).where(WorkOrder.id == work_order_id, WorkOrder.is_deleted.is_(False))
        if with_relations:
            statement = statement.options(selectinload(WorkOrder.attachments), selectinload(WorkOrder.events))
        return await self.session.scalar(statement)

    async def get_by_request_id(self, request_id: str) -> WorkOrder | None:
        return await self.session.scalar(select(WorkOrder).where(WorkOrder.request_id == request_id))

    async def list(self, *, status: str | None = None, reporter_id: int | None = None, assignee_id: int | None = None, area: str | None = None, page: int = 1, page_size: int = 20) -> tuple[list[WorkOrder], int]:
        filters = [WorkOrder.is_deleted.is_(False)]
        if status:
            filters.append(WorkOrder.status == status)
        if reporter_id:
            filters.append(WorkOrder.reporter_id == reporter_id)
        if assignee_id:
            filters.append(WorkOrder.assignee_id == assignee_id)
        if area:
            filters.append(WorkOrder.area == area)
        total = await self.session.scalar(select(func.count(WorkOrder.id)).where(*filters)) or 0
        rows = await self.session.scalars(select(WorkOrder).where(*filters).order_by(WorkOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
        return list(rows.all()), total

    async def create(self, order: WorkOrder) -> WorkOrder:
        self.session.add(order)
        await self.session.flush()
        return order

    async def add_event(self, event: WorkOrderEvent) -> None:
        self.session.add(event)
        await self.session.flush()
