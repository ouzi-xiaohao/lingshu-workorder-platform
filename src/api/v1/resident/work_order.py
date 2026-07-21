from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import current_user, db_session
from src.dao.work_order_dao import WorkOrderDAO
from src.models.user import User
from src.schemas.request.work_order import RatingRequest, StatusUpdateRequest, WorkOrderCreate
from src.schemas.response.work_order import WorkOrderDetail, WorkOrderSummary
from src.service.work_order_service import WorkOrderService


router = APIRouter()


@router.post("", status_code=202)
async def create_work_order(payload: WorkOrderCreate, request: Request, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    order = await WorkOrderService(session).create(payload, user.id, request.state.trace_id)
    return {"code": "ACCEPTED", "message": "工单已创建并完成初步智能识别", "data": WorkOrderDetail.model_validate(order)}


@router.get("")
async def list_my_work_orders(status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    items, total = await WorkOrderDAO(session).list(status=status, reporter_id=user.id, page=page, page_size=page_size)
    return {"code": "OK", "data": {"items": [WorkOrderSummary.model_validate(item) for item in items], "total": total, "page": page, "page_size": page_size}}


@router.get("/{work_order_id}")
async def get_my_work_order(work_order_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    order = await WorkOrderService(session).detail(work_order_id)
    if order.reporter_id != user.id:
        from fastapi import HTTPException
        raise HTTPException(403, "只能查看本人提交的工单")
    return {"code": "OK", "data": WorkOrderDetail.model_validate(order)}


@router.post("/{work_order_id}/rating")
async def rate_work_order(work_order_id: int, payload: RatingRequest, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    order = await WorkOrderService(session).detail(work_order_id)
    if order.reporter_id != user.id:
        from fastapi import HTTPException
        raise HTTPException(403, "只能评价本人提交的工单")
    if order.status != "已完成":
        from fastapi import HTTPException
        raise HTTPException(409, "只能评价已完成的工单")
    order.rating = payload.score
    await session.commit()
    return {"code": "OK", "message": "评价已提交", "data": {"score": payload.score, "comment": payload.comment}}


@router.post("/{work_order_id}/cancel")
async def cancel_work_order(work_order_id: int, payload: StatusUpdateRequest, request: Request, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    order = await WorkOrderService(session).detail(work_order_id)
    if order.reporter_id != user.id:
        from fastapi import HTTPException
        raise HTTPException(403, "只能取消本人提交的工单")
    if payload.status != "已取消":
        from fastapi import HTTPException
        raise HTTPException(422, "取消操作的目标状态必须为已取消")
    updated = await WorkOrderService(session).transition(work_order_id, "已取消", user.id, "resident", payload.detail, request.state.trace_id)
    return {"code": "OK", "message": "工单已取消", "data": WorkOrderDetail.model_validate(updated)}
