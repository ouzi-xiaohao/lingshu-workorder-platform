from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.credit import CreditRecord


class CreditDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, record: CreditRecord) -> CreditRecord:
        self.session.add(record)
        await self.session.flush()
        return record

    async def list_by_user(self, user_id: int) -> list[CreditRecord]:
        return list((await self.session.scalars(select(CreditRecord).where(CreditRecord.user_id == user_id).order_by(CreditRecord.created_at.desc()))).all())
