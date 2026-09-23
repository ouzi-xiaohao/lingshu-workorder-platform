from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.engine import AgentEngine
from src.agent.order_flow_agent import OrderFlowAgent
from src.common.cache import invalidate_worker
from src.common.redis_tools import coordination
from src.common.tracing import bind_log_context, traced
from src.core.error_code import ErrorCode
from src.core.exceptions import BusinessError
from src.dao.work_order_dao import WorkOrderDAO
from src.dao.worker_dao import WorkerDAO
from src.models.work_order import WorkOrderEvent


class DispatchService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.orders = WorkOrderDAO(session)
        self.workers = WorkerDAO(session)

    async def dispatch(self, work_order_id: int, trace_id: str, specified_worker_id: int | None = None, force: bool = False):
        async with coordination.lock(f"dispatch:order:{work_order_id}"):
            order = await self.orders.get(work_order_id, with_relations=False)
            if not order:
                raise BusinessError("工单不存在", ErrorCode.WORK_ORDER_NOT_FOUND, 404)
            bind_log_context(order_id=order.id, order_no=order.order_no, root_trace_id=order.trace_id)
            if order.assignee_id and not force:
                return order, {"message": "工单已派单，幂等返回"}
            if order.status not in {"待派单", "已派单"}:
                raise BusinessError("当前状态不允许派单", ErrorCode.INVALID_TRANSITION)
            if order.status == "待派单":
                flow = await OrderFlowAgent().run({"current_status": order.status, "target_status": "已派单"})
                if not flow.success:
                    raise BusinessError(flow.message, ErrorCode.INVALID_TRANSITION)
            async with traced("work_order.dispatch", specified_worker_id=specified_worker_id):
                # Fetch the available pool once. The agent first tries local workers and
                # may deliberately expand to cross-area workers when its plan requires it.
                profiles = await self.workers.list_available()
                candidates = [{
                    "user_id": profile.user_id, "display_name": profile.user.display_name,
                    "skills": profile.skills, "longitude": profile.longitude, "latitude": profile.latitude,
                    "current_load": profile.current_load, "max_load": profile.max_load, "rating": profile.rating,
                    "area": profile.user.area,
                } for profile in profiles if not specified_worker_id or profile.user_id == specified_worker_id]
                previous_assignee_id = order.assignee_id
                state, results = await AgentEngine.with_builtins().run(trace_id, {
                    "category": order.category, "priority": order.priority, "area": order.area,
                    "longitude": order.longitude, "latitude": order.latitude,
                    "worker_candidates": candidates,
                }, names=["dispatch-agent"])
                if not results[-1].success:
                    raise BusinessError(results[-1].message, ErrorCode.NO_WORKER_AVAILABLE)
                worker_id = int(state["worker_id"])
                if previous_assignee_id and previous_assignee_id != worker_id:
                    await self.workers.adjust_load(previous_assignee_id, -1)
                if previous_assignee_id != worker_id:
                    await self.workers.adjust_load(worker_id, 1)
                order.assignee_id = worker_id
                order.status = "已派单"
                await self.orders.add_event(WorkOrderEvent(
                    work_order_id=order.id,
                    actor_type="dispatch-agent",
                    action="dispatched",
                    from_status="待派单" if not previous_assignee_id else "已派单",
                    to_status="已派单",
                    detail=(
                        f"派单给 {state['worker_name']}，策略 {state['strategy']}，"
                        f"评分 {state['dispatch_score']}，距离 {state['distance_km']}km，"
                        f"置信度 {state['confidence']}"
                    ),
                    trace_id=trace_id,
                ))
                await self.session.commit()
                await invalidate_worker(worker_id)
                if previous_assignee_id:
                    await invalidate_worker(previous_assignee_id)
                return await self.orders.get(order.id), state
