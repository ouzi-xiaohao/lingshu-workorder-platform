from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.credit_agent import CreditAgent
from src.dao.credit_dao import CreditDAO
from src.dao.user_dao import UserDAO
from src.models.credit import CreditRecord


class CreditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def settle(self, work_order, rating: float | None = None):
        if not work_order.assignee_id:
            return None
        result = await CreditAgent().run({"status": work_order.status, "rating": rating, "on_time": True})
        delta = int(result.output["credit_delta"])
        user = await UserDAO(self.session).get(work_order.assignee_id)
        if not user or not delta:
            return None
        user.credit_balance += delta
        record = await CreditDAO(self.session).create(CreditRecord(user_id=user.id, work_order_id=work_order.id, delta=delta, balance_after=user.credit_balance, reason=str(result.output["credit_reason"])))
        await self.session.commit()
        return record
