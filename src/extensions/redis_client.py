import asyncio

from src.common.circuit_breaker import CircuitOpenError, CircuitState, circuits
from src.core.config import settings


def reject_if_redis_open() -> None:
    breaker = circuits.get("redis")
    if breaker.state is CircuitState.OPEN:
        raise CircuitOpenError(breaker.name, breaker.retry_after)


class RedisClient:
    def __init__(self):
        self.client = None

    async def connect(self):
        if self.client:
            return self.client
        reject_if_redis_open()
        from redis.asyncio import from_url

        client = from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.3,
            socket_timeout=0.5,
        )
        try:
            await asyncio.wait_for(client.ping(), timeout=0.4)
        except Exception:
            try:
                await client.aclose()
            except Exception:
                pass
            raise
        self.client = client
        return self.client

    async def invalidate(self) -> None:
        client = self.client
        self.client = None
        if client:
            try:
                await client.aclose()
            except Exception:
                pass

    async def close(self):
        await self.invalidate()


redis_client = RedisClient()
