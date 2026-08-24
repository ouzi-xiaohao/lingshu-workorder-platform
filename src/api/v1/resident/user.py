from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import current_user, db_session
from src.dao.credit_dao import CreditDAO
from src.models.user import User


router = APIRouter()


@router.get("/me")
async def me(user: User = Depends(current_user)):
    return {"code": "OK", "data": {"id": user.id, "username": user.username, "display_name": user.display_name, "role": user.role, "area": user.area, "credit_balance": user.credit_balance}}


@router.get("/credits")
async def credits(user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    records = await CreditDAO(session).list_by_user(user.id)
    return {"code": "OK", "data": {"balance": user.credit_balance, "records": [{"delta": item.delta, "reason": item.reason, "balance_after": item.balance_after, "created_at": item.created_at} for item in records]}}
