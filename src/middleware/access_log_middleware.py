from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware

from src.common.logger import logger
from src.common.tracing import extra


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = perf_counter()
        response = await call_next(request)
        logger.info(
            "http.request",
            extra=extra(
                span="http.request",
                method=request.method,
                path=request.url.path,
                http_status=response.status_code,
                duration_ms=round((perf_counter() - started) * 1000, 2),
            ),
        )
        return response
