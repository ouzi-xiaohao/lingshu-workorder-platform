from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import db_session
from src.schemas.request.auth import LoginRequest, RegisterRequest
from src.service.user_service import UserService


router = APIRouter()


@router.post("/login")
async def login(payload: LoginRequest, session: AsyncSession = Depends(db_session)):
    result = await UserService(session).authenticate(payload.username, payload.password)
    if not result:
        raise HTTPException(401, "用户名或密码错误")
    user, token = result
    return {"code": "OK", "data": {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "display_name": user.display_name, "role": user.role}}}


@router.post("/register", status_code=201)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(db_session)):
    try:
        user = await UserService(session).register_resident(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"code": "OK", "data": {"id": user.id, "username": user.username, "display_name": user.display_name}}
