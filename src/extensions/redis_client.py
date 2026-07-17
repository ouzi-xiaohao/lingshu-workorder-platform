from src.core.config import settings


class RedisClient:
    def __init__(self):
        self.client = None

    async def connect(self):
        try:
            from redis.asyncio import from_url
            self.client = from_url(settings.redis_url, decode_responses=True)
            await self.client.ping()
        except Exception:
            self.client = None
        return self.client

    async def close(self):
        if self.client:
            await self.client.aclose()


redis_client = RedisClient()
