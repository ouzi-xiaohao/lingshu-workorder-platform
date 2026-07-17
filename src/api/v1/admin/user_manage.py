from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import db_session, require_roles
from src.dao.user_dao import UserDAO
from src.models.user import User


router = APIRouter()


@router.get("")
async def users(role: str | None = None, _: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    items = await UserDAO(session).list(role)
    return {"code": "OK", "data": [{"id": user.id, "username": user.username, "display_name": user.display_name, "role": user.role, "area": user.area, "active": user.is_active} for user in items]}


@router.patch("/{user_id}/active")
async def set_active(user_id: int, active: bool, _: User = Depends(require_roles("admin")), session: AsyncSession = Depends(db_session)):
    user = await UserDAO(session).get(user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(404, "用户不存在")
    user.is_active = active
    await session.commit()
    return {"code": "OK", "data": {"id": user.id, "active": user.is_active}}
