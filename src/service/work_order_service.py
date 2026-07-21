from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.intent_agent import IntentAgent
from src.agent.order_flow_agent import OrderFlowAgent
from src.agent.scheduler import AgentScheduler
from src.ai_services.multimodal_fusion import MultimodalFusionService
from src.common.id_generator import new_order_no
from src.core.error_code import ErrorCode
from src.core.exceptions import BusinessError
from src.dao.work_order_dao import WorkOrderDAO
from src.models.work_order import Attachment, WorkOrder, WorkOrderEvent
from src.schemas.request.work_order import WorkOrderCreate


class WorkOrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dao = WorkOrderDAO(session)
        self.fusion = MultimodalFusionService()

    async def create(self, payload: WorkOrderCreate, reporter_id: int, trace_id: str) -> WorkOrder:
        if payload.request_id:
            existing = await self.dao.get_by_request_id(payload.request_id)
            if existing:
                return existing
        for item in payload.attachments:
            if not item.object_key.startswith(f"users/{reporter_id}/"):
                raise BusinessError("附件不属于当前用户", ErrorCode.FORBIDDEN, 403)
        attachments = [Attachment(**item.model_dump()) for item in payload.attachments]
        fused = await self.fusion.fuse(payload.title, payload.description, attachments)
        state, results = await AgentScheduler([IntentAgent()]).execute(trace_id, {
            **fused, "area": payload.area, "longitude": payload.longitude, "latitude": payload.latitude,
        })
        order = WorkOrder(
            order_no=new_order_no(), request_id=payload.request_id, title=payload.title, description=payload.description,
            normalized_summary=str(state["normalized_text"]), category=str(state["category"]), priority=str(state["priority"]),
            status="待派单", area=payload.area, longitude=payload.longitude, latitude=payload.latitude,
            reporter_id=reporter_id, confidence=float(state["confidence"]), trace_id=trace_id,
            sla_deadline=datetime.now(timezone.utc) + timedelta(hours=1 if state["priority"] == "紧急" else 4),
            attachments=attachments,
        )
        await self.dao.create(order)
        await self.dao.add_event(WorkOrderEvent(work_order_id=order.id, actor_id=reporter_id, actor_type="resident", action="created", to_status="待派单", detail=f"意图识别完成：{state['category']}，置信度 {state['confidence']}", trace_id=trace_id))
        await self.session.commit()
        return await self.dao.get(order.id)

    async def transition(self, work_order_id: int, target_status: str, actor_id: int, actor_type: str, detail: str, trace_id: str) -> WorkOrder:
        order = await self.dao.get(work_order_id, with_relations=False)
        if not order:
            raise BusinessError("工单不存在", ErrorCode.WORK_ORDER_NOT_FOUND, 404)
        result = await OrderFlowAgent().run({"current_status": order.status, "target_status": target_status})
        if not result.success:
            raise BusinessError(result.message, ErrorCode.INVALID_TRANSITION)
        previous = order.status
        order.status = target_status
        if target_status == "已完成":
            order.completed_at = datetime.now(timezone.utc)
        await self.dao.add_event(WorkOrderEvent(work_order_id=order.id, actor_id=actor_id, actor_type=actor_type, action="status_changed", from_status=previous, to_status=target_status, detail=detail, trace_id=trace_id))
        await self.session.commit()
        return await self.dao.get(order.id)

    async def detail(self, work_order_id: int) -> WorkOrder:
        order = await self.dao.get(work_order_id)
        if not order:
            raise BusinessError("工单不存在", ErrorCode.WORK_ORDER_NOT_FOUND, 404)
        return order
