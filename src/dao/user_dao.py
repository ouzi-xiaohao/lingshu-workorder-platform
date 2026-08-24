from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


class UserDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        return await self.session.scalar(select(User).where(User.username == username, User.is_deleted.is_(False)))

    async def list(self, role: str | None = None) -> list[User]:
        statement = select(User).where(User.is_deleted.is_(False)).order_by(User.id)
        if role:
            statement = statement.where(User.role == role)
        return list((await self.session.scalars(statement)).all())

    async def create(self, **values) -> User:
        user = User(**values)
        self.session.add(user)
        await self.session.flush()
        return user
