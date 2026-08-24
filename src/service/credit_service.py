from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.tools.credit import compute_credit_delta
from src.common.cache import invalidate_worker
from src.common.tracing import bind_log_context, traced
from src.dao.credit_dao import CreditDAO
from src.dao.user_dao import UserDAO
from src.models.credit import CreditRecord


class CreditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def settle(self, work_order, rating: float | None = None):
        if not work_order.assignee_id:
            return None
        bind_log_context(order_id=work_order.id, order_no=work_order.order_no, root_trace_id=work_order.trace_id)
        async with traced("credit.settle", assignee_id=work_order.assignee_id):
            result = compute_credit_delta(
                status=work_order.status,
                rating=rating,
                sla_deadline=work_order.sla_deadline,
                completed_at=work_order.completed_at,
            )
            delta = int(result.delta)
            user = await UserDAO(self.session).get(work_order.assignee_id)
            if not user or not delta:
                return None
            user.credit_balance += delta
            record = await CreditDAO(self.session).create(CreditRecord(user_id=user.id, work_order_id=work_order.id, delta=delta, balance_after=user.credit_balance, reason=result.reason))
            await self.session.commit()
            await invalidate_worker(user.id)
            return record
