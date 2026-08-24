from collections.abc import Callable

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.tracing import bind_log_context
from src.core.security import decode_access_token
from src.dao.user_dao import UserDAO
from src.extensions.postgres import get_session
from src.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)


async def db_session(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session


async def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), session: AsyncSession = Depends(get_session)) -> User:
    if not credentials:
        raise HTTPException(401, "缺少访问令牌")
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "访问令牌无效或已过期")
    user = await UserDAO(session).get(int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "用户不存在或已停用")
    bind_log_context(user_id=user.id, username=user.username, role=user.role)
    return user


def require_roles(*roles: str) -> Callable:
    async def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "无权执行此操作")
        return user
    return dependency
