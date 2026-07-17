from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, hash_password, verify_password
from src.dao.user_dao import UserDAO
from src.extensions.postgres import AsyncSessionLocal
from src.models.user import WorkerProfile


BOOTSTRAP_USERS = [
    ("resident", "resident123", "居民示例", "resident", "中心区", None),
    ("worker", "worker123", "李昂", "worker", "全园区", {"skills": "暖通空调/智能终端", "current_load": 1, "max_load": 4, "rating": 93}),
    ("admin", "admin123", "林悦", "admin", "全园区", None),
]


async def ensure_bootstrap_users() -> None:
    async with AsyncSessionLocal() as session:
        dao = UserDAO(session)
        for username, password, display_name, role, area, profile in BOOTSTRAP_USERS:
            if await dao.get_by_username(username):
                continue
            user = await dao.create(username=username, password_hash=hash_password(password), display_name=display_name, role=role, area=area)
            if profile:
                session.add(WorkerProfile(user_id=user.id, **profile))
        await session.commit()


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dao = UserDAO(session)

    async def authenticate(self, username: str, password: str) -> tuple[object, str] | None:
        user = await self.dao.get_by_username(username)
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            return None
        return user, create_access_token(str(user.id), user.role)

    async def register_resident(self, **values):
        if await self.dao.get_by_username(values["username"]):
            raise ValueError("用户名已存在")
        values["password_hash"] = hash_password(values.pop("password"))
        values["role"] = "resident"
        user = await self.dao.create(**values)
        await self.session.commit()
        return user
