from collections import defaultdict, deque
from time import monotonic, time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.common.circuit_breaker import circuits
from src.core.config import settings
from src.extensions.redis_client import redis_client


_SKIP_PATHS = {"/health", "/health/ready", "/docs", "/openapi.json", "/redoc"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests: defaultdict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request, call_next):
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)
        key = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "unknown")
        allowed = await self._allowed(key.split(",")[0].strip())
        if not allowed:
            return JSONResponse({"code": "COMMON_429", "message": "请求过于频繁，请稍后再试"}, status_code=429)
        return await call_next(request)

    async def _allowed(self, key: str) -> bool:
        breaker = circuits.get("redis")
        if breaker.allow_request():
            try:
                client = await redis_client.connect()
                bucket = f"lingshu:ratelimit:{key}:{int(time()) // 60}"
                count = int(await client.incr(bucket))
                if count == 1:
                    await client.expire(bucket, 70)
                breaker.record_success()
                return count <= settings.rate_limit_per_minute
            except Exception:
                breaker.record_failure()
                await redis_client.invalidate()
        return self._local_allowed(key)

    def _local_allowed(self, key: str) -> bool:
        now = monotonic()
        bucket = self.requests[key]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= settings.rate_limit_per_minute:
            return False
        bucket.append(now)
        return True
