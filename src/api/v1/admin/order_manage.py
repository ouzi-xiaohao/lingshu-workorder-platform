from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import db_session, require_roles
from src.dao.work_order_dao import WorkOrderDAO
from src.models.user import User
from src.models.work_order import WorkOrderEvent
from src.schemas.request.human_review import HumanReviewResolve
from src.schemas.request.work_order import DispatchRequest
from src.schemas.response.work_order import WorkOrderDetail, WorkOrderSummary
from src.service.dispatch_service import DispatchService
from src.service.work_order_service import WorkOrderService


router = APIRouter()


@router.get("")
async def all_orders(status: str | None = None, area: str | None = None, trace_id: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), _: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    items, total = await WorkOrderDAO(session).list(status=status, area=area, trace_id=trace_id, page=page, page_size=page_size)
    return {"code": "OK", "data": {"items": [WorkOrderSummary.model_validate(item) for item in items], "total": total, "page": page, "page_size": page_size}}


@router.get("/human-review")
async def pending_human_review(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), _: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    items, total = await WorkOrderService(session).list_pending_human_review(page=page, page_size=page_size)
    return {"code": "OK", "data": {"items": [WorkOrderSummary.model_validate(item) for item in items], "total": total, "page": page, "page_size": page_size}}


@router.get("/{work_order_id}")
async def detail(work_order_id: int, _: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    return {"code": "OK", "data": WorkOrderDetail.model_validate(await WorkOrderService(session).detail(work_order_id))}


@router.post("/{work_order_id}/dispatch")
async def dispatch(work_order_id: int, payload: DispatchRequest, request: Request, _: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    order, decision = await DispatchService(session).dispatch(work_order_id, request.state.trace_id, payload.worker_id, payload.force)
    return {"code": "OK", "message": "智能派单完成", "data": {"work_order": WorkOrderDetail.model_validate(order), "decision": decision}}


@router.post("/{work_order_id}/human-review")
async def resolve_human_review(work_order_id: int, payload: HumanReviewResolve, request: Request, admin: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    order = await WorkOrderService(session).resolve_human_review(work_order_id, payload, admin.id, request.state.trace_id)
    return {"code": "OK", "message": "人工审核完成", "data": WorkOrderDetail.model_validate(order)}


@router.post("/{work_order_id}/supervise")
async def supervise(work_order_id: int, request: Request, admin: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    order = await WorkOrderService(session).detail(work_order_id)
    session.add(WorkOrderEvent(work_order_id=order.id, actor_id=admin.id, actor_type="admin", action="supervised", detail="管理员发起督办", trace_id=request.state.trace_id))
    await session.commit()
    return {"code": "OK", "message": "已发起督办"}
