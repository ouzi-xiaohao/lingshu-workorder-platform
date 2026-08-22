from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.engine import AgentEngine
from src.agent.order_flow_agent import OrderFlowAgent
from src.ai_services.multimodal_fusion import MultimodalFusionService
from src.common.cache import invalidate_stats, invalidate_worker
from src.common.id_generator import new_order_no
from src.common.logger import logger
from src.common.redis_tools import coordination
from src.common.tracing import bind_log_context, traced
from src.core.config import settings
from src.core.error_code import ErrorCode
from src.core.exceptions import BusinessError
from src.dao.work_order_dao import WorkOrderDAO
from src.dao.worker_dao import WorkerDAO
from src.models.work_order import Attachment, WorkOrder, WorkOrderEvent
from src.schemas.request.work_order import WorkOrderCreate


def _has_media(attachments: list[object]) -> bool:
    return any(str(getattr(item, "media_type", "")) in {"audio", "image", "video"} for item in attachments)


def enqueue_ai_enrichment(order_id: int, trace_id: str) -> bool:
    if not settings.ai_async_enabled:
        return False
    try:
        from src.tasks.ai_tasks import enrich_work_order

        enrich_work_order.apply_async(args=(order_id, trace_id))
        return True
    except Exception as exc:
        logger.warning("ai.enqueue.failed", extra={"order_id": order_id, "error": str(exc)})
        return False


async def enrich_work_order_record(order_id: int, trace_id: str) -> dict[str, object]:
    from src.extensions.postgres import AsyncSessionLocal

    async with coordination.lock(f"enrich:order:{order_id}"):
        async with AsyncSessionLocal() as session:
            return await WorkOrderService(session).enrich(order_id, trace_id)


class WorkOrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dao = WorkOrderDAO(session)
        self.workers = WorkerDAO(session)
        self.fusion = MultimodalFusionService()

    async def create(self, payload: WorkOrderCreate, reporter_id: int, trace_id: str) -> WorkOrder:
        bind_log_context(reporter_id=reporter_id, request_id=payload.request_id, root_trace_id=trace_id)
        async with traced("work_order.create"):
            if payload.request_id:
                existing = await self.dao.get_by_request_id(payload.request_id)
                if existing:
                    bind_log_context(order_id=existing.id, order_no=existing.order_no, root_trace_id=existing.trace_id)
                    return existing
            for item in payload.attachments:
                if not item.object_key.startswith(f"users/{reporter_id}/"):
                    raise BusinessError("附件不属于当前用户", ErrorCode.FORBIDDEN, 403)
            attachments = [Attachment(**item.model_dump()) for item in payload.attachments]
            defer_ai = _has_media(attachments) and settings.ai_async_enabled
            async with traced("multimodal.fuse", attachment_count=len(attachments), heavy=not defer_ai):
                fused = await self.fusion.fuse(payload.title, payload.description, attachments, heavy=not defer_ai)
            state, _results = await AgentEngine.with_builtins().run(trace_id, {
                **fused, "area": payload.area, "longitude": payload.longitude, "latitude": payload.latitude,
            }, names=["intent-agent"])
            order = WorkOrder(
                order_no=new_order_no(), request_id=payload.request_id, title=payload.title, description=payload.description,
                normalized_summary=str(state["normalized_text"]), category=str(state["category"]), priority=str(state["priority"]),
                status="待派单", area=payload.area, longitude=payload.longitude, latitude=payload.latitude,
                reporter_id=reporter_id, confidence=float(state["confidence"]), trace_id=trace_id,
                sla_deadline=datetime.now(timezone.utc) + timedelta(hours=1 if state["priority"] == "紧急" else 4),
                attachments=attachments,
            )
            await self.dao.create(order)
            bind_log_context(order_id=order.id, order_no=order.order_no)
            await self.dao.add_event(WorkOrderEvent(work_order_id=order.id, actor_id=reporter_id, actor_type="resident", action="created", to_status="待派单", detail=f"意图识别完成：{state['category']}，置信度 {state['confidence']}", trace_id=trace_id))
            await self.session.commit()
            if defer_ai:
                enqueue_ai_enrichment(order.id, trace_id)
            return await self.dao.get(order.id)

    async def enrich(self, work_order_id: int, trace_id: str) -> dict[str, object]:
        order = await self.dao.get(work_order_id)
        if not order:
            return {"status": "missing", "order_id": work_order_id}
        bind_log_context(order_id=order.id, order_no=order.order_no, root_trace_id=order.trace_id)
        async with traced("work_order.enrich"):
            if any(event.action == "ai_enriched" for event in order.events):
                return {"status": "already", "order_id": order.id}
            fused = await self.fusion.fuse(order.title, order.description, order.attachments, heavy=True)
            state, _results = await AgentEngine.with_builtins().run(trace_id, {
                **fused,
                "area": order.area,
                "longitude": order.longitude,
                "latitude": order.latitude,
                "category": order.category,
                "priority": order.priority,
                "confidence": order.confidence,
            }, names=["intent-agent"])
            order.normalized_summary = str(state.get("normalized_text") or order.normalized_summary)
            if order.status == "待派单":
                order.category = str(state.get("category") or order.category)
                order.priority = str(state.get("priority") or order.priority)
                order.confidence = float(state.get("confidence") or order.confidence)
                if order.priority == "紧急":
                    order.sla_deadline = datetime.now(timezone.utc) + timedelta(hours=1)
            await self.dao.add_event(WorkOrderEvent(
                work_order_id=order.id, actor_type="system", action="ai_enriched",
                to_status=order.status,
                detail=f"多模态补全完成：{order.category}，置信度 {order.confidence}",
                trace_id=trace_id,
            ))
            await self.session.commit()
            await invalidate_stats()
            return {"status": "enriched", "order_id": order.id, "category": order.category}

    async def transition(self, work_order_id: int, target_status: str, actor_id: int, actor_type: str, detail: str, trace_id: str) -> WorkOrder:
        order = await self.dao.get(work_order_id, with_relations=False)
        if not order:
            raise BusinessError("工单不存在", ErrorCode.WORK_ORDER_NOT_FOUND, 404)
        bind_log_context(order_id=order.id, order_no=order.order_no, root_trace_id=order.trace_id)
        async with traced("work_order.transition", from_status=order.status, to_status=target_status):
            result = await OrderFlowAgent().run({"current_status": order.status, "target_status": target_status})
            if not result.success:
                raise BusinessError(result.message, ErrorCode.INVALID_TRANSITION)
            previous = order.status
            order.status = target_status
            if target_status == "已完成":
                order.completed_at = datetime.now(timezone.utc)
            if target_status in {"已完成", "已取消"}:
                await self.workers.adjust_load(order.assignee_id, -1)
            await self.dao.add_event(WorkOrderEvent(work_order_id=order.id, actor_id=actor_id, actor_type=actor_type, action="status_changed", from_status=previous, to_status=target_status, detail=detail, trace_id=trace_id))
            await self.session.commit()
            await invalidate_worker(order.assignee_id)
            return await self.dao.get(order.id)

    async def detail(self, work_order_id: int) -> WorkOrder:
        order = await self.dao.get(work_order_id)
        if not order:
            raise BusinessError("工单不存在", ErrorCode.WORK_ORDER_NOT_FOUND, 404)
        return order
