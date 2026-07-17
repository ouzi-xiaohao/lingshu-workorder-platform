from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.router import api_router
from src.core.config import settings
from src.core.exceptions import register_exception_handlers
from src.extensions.postgres import dispose_db, init_db
from src.middleware.access_log_middleware import AccessLogMiddleware
from src.middleware.rate_limit_middleware import RateLimitMiddleware
from src.middleware.trace_middleware import TraceMiddleware
from src.service.user_service import ensure_bootstrap_users


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    await ensure_bootstrap_users()
    yield
    await dispose_db()


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="多模态接入、多智能体协同调度与工单全生命周期管理 API",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(AccessLogMiddleware)
    application.add_middleware(TraceMiddleware)
    application.include_router(api_router, prefix=settings.api_prefix)
    register_exception_handlers(application)

    @application.get("/health", tags=["系统"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name, "version": settings.app_version}

    return application
