from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import db_session, require_roles
from src.dao.work_order_dao import WorkOrderDAO
from src.models.user import User
from src.schemas.request.work_order import StatusUpdateRequest
from src.schemas.response.work_order import WorkOrderDetail, WorkOrderSummary
from src.service.credit_service import CreditService
from src.service.work_order_service import WorkOrderService


router = APIRouter()


@router.get("")
async def assigned_orders(status: str | None = None, page: int = Query(1, ge=1), worker: User = Depends(require_roles("worker", "admin")), session: AsyncSession = Depends(db_session)):
    items, total = await WorkOrderDAO(session).list(status=status, assignee_id=worker.id, page=page)
    return {"code": "OK", "data": {"items": [WorkOrderSummary.model_validate(item) for item in items], "total": total}}


@router.post("/{work_order_id}/status")
async def update_status(work_order_id: int, payload: StatusUpdateRequest, request: Request, worker: User = Depends(require_roles("worker", "admin")), session: AsyncSession = Depends(db_session)):
    order = await WorkOrderService(session).detail(work_order_id)
    if worker.role != "admin" and order.assignee_id != worker.id:
        from fastapi import HTTPException
        raise HTTPException(403, "只能处理分配给自己的工单")
    updated = await WorkOrderService(session).transition(work_order_id, payload.status, worker.id, worker.role, payload.detail, request.state.trace_id)
    if payload.status == "已完成":
        await CreditService(session).settle(updated, updated.rating)
    return {"code": "OK", "data": WorkOrderDetail.model_validate(updated)}
