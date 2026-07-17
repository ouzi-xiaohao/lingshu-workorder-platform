from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware

from src.common.logger import logger


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = perf_counter()
        response = await call_next(request)
        logger.info("request method=%s path=%s status=%s duration_ms=%.2f", request.method, request.url.path, response.status_code, (perf_counter() - started) * 1000)
        return response
