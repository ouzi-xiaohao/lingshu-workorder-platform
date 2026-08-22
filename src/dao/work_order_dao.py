from __future__ import annotations

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.work_order import Attachment, WorkOrder, WorkOrderEvent


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

    async def list(self, *, status: str | None = None, reporter_id: int | None = None, assignee_id: int | None = None, area: str | None = None, trace_id: str | None = None, page: int = 1, page_size: int = 20) -> tuple[list[WorkOrder], int]:
        filters = [WorkOrder.is_deleted.is_(False)]
        if status:
            filters.append(WorkOrder.status == status)
        if reporter_id:
            filters.append(WorkOrder.reporter_id == reporter_id)
        if assignee_id:
            filters.append(WorkOrder.assignee_id == assignee_id)
        if area:
            filters.append(WorkOrder.area == area)
        if trace_id:
            filters.append(or_(
                WorkOrder.trace_id == trace_id,
                exists().where(WorkOrderEvent.work_order_id == WorkOrder.id, WorkOrderEvent.trace_id == trace_id),
            ))
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

    async def list_pending_ai_enrichment(self, limit: int = 10) -> list[int]:
        enriched = exists().where(WorkOrderEvent.work_order_id == WorkOrder.id, WorkOrderEvent.action == "ai_enriched")
        has_media = exists().where(
            Attachment.work_order_id == WorkOrder.id,
            Attachment.media_type.in_(("audio", "image", "video")),
        )
        rows = await self.session.scalars(
            select(WorkOrder.id).where(
                WorkOrder.is_deleted.is_(False),
                WorkOrder.status == "待派单",
                has_media,
                ~enriched,
            ).order_by(WorkOrder.created_at.asc()).limit(limit)
        )
        return list(rows.all())
