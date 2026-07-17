from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.dispatch_agent import DispatchAgent
from src.agent.scheduler import AgentScheduler
from src.common.redis_tools import coordination
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
            if order.assignee_id and not force:
                return order, {"message": "工单已派单，幂等返回"}
            profiles = await self.workers.list_available(order.area)
            candidates = [{
                "user_id": profile.user_id, "display_name": profile.user.display_name,
                "skills": profile.skills, "longitude": profile.longitude, "latitude": profile.latitude,
                "current_load": profile.current_load, "max_load": profile.max_load, "rating": profile.rating,
            } for profile in profiles if not specified_worker_id or profile.user_id == specified_worker_id]
            state, results = await AgentScheduler([DispatchAgent()]).execute(trace_id, {
                "category": order.category, "longitude": order.longitude, "latitude": order.latitude,
                "worker_candidates": candidates,
            })
            if not results[-1].success:
                raise BusinessError(results[-1].message, ErrorCode.NO_WORKER_AVAILABLE)
            profile = await self.workers.get_by_user_id(int(state["worker_id"]))
            order.assignee_id = int(state["worker_id"])
            order.status = "已派单"
            if profile:
                profile.current_load += 1
                profile.work_status = "busy" if profile.current_load >= profile.max_load else "available"
            await self.orders.add_event(WorkOrderEvent(work_order_id=order.id, actor_type="dispatch-agent", action="dispatched", from_status="待派单", to_status="已派单", detail=f"派单给 {state['worker_name']}，评分 {state['dispatch_score']}，距离 {state['distance_km']}km", trace_id=trace_id))
            await self.session.commit()
            return await self.orders.get(order.id), state
