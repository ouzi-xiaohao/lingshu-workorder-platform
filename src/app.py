import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.v1.router import api_router
from src.common.circuit_breaker import CircuitOpenError, CircuitState, circuits
from src.core.config import settings
from src.core.exceptions import register_exception_handlers
from src.core.runtime import validate_runtime_settings
from src.extensions.postgres import dispose_db, init_db, ping_db
from src.extensions.redis_client import redis_client
from src.middleware.access_log_middleware import AccessLogMiddleware
from src.middleware.rate_limit_middleware import RateLimitMiddleware
from src.middleware.trace_middleware import TraceMiddleware
from src.service.user_service import ensure_bootstrap_users


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_runtime_settings()
    await init_db()
    if str(settings.environment).lower() != "production":
        await ensure_bootstrap_users()
    from src.common.cache import cache

    listener = asyncio.create_task(cache.listen_invalidations())
    yield
    listener.cancel()
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

    @application.get("/health/ready", tags=["系统"])
    async def ready():
        checks: dict[str, object] = {}
        try:
            await ping_db()
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"
        redis_breaker = circuits.get("redis")
        if redis_breaker.state is CircuitState.OPEN:
            checks["redis"] = "unavailable"
        else:
            try:
                await redis_client.connect()
                checks["redis"] = "ok"
                redis_breaker.record_success()
            except CircuitOpenError:
                checks["redis"] = "unavailable"
            except Exception:
                redis_breaker.record_failure()
                await redis_client.invalidate()
                checks["redis"] = "unavailable"
        checks["circuits"] = {item["name"]: item["state"] for item in circuits.snapshot()}
        database_ok = checks["database"] == "ok"
        status = "ok" if database_ok and checks["redis"] == "ok" else "degraded" if database_ok else "unavailable"
        return JSONResponse(
            {"status": status, "service": settings.app_name, "version": settings.app_version, "checks": checks},
            status_code=200 if database_ok else 503,
        )

    return application
