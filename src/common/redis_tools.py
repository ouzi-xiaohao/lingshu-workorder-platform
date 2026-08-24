import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager

from src.common.circuit_breaker import circuits
from src.extensions.redis_client import redis_client


class LocalCoordinationFallback:
    def __init__(self):
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    @asynccontextmanager
    async def lock(self, key: str, timeout: float = 5):
        lock = self._locks[key]
        await asyncio.wait_for(lock.acquire(), timeout)
        try:
            yield
        finally:
            lock.release()


class Coordination:
    def __init__(self):
        self.local = LocalCoordinationFallback()

    @asynccontextmanager
    async def lock(self, key: str, timeout: float = 5):
        breaker = circuits.get("redis")
        redis_lock = None
        if breaker.allow_request():
            try:
                client = await redis_client.connect()
                redis_lock = client.lock(f"lingshu:{key}", timeout=max(int(timeout), 1), blocking_timeout=timeout)
                acquired = await redis_lock.acquire()
                if not acquired:
                    breaker.record_success()
                    raise TimeoutError(f"redis lock timeout: {key}")
                breaker.record_success()
            except TimeoutError:
                raise
            except Exception:
                breaker.record_failure()
                redis_lock = None
                await redis_client.invalidate()
        if redis_lock is None:
            async with self.local.lock(key, timeout):
                yield
            return
        try:
            yield
        finally:
            try:
                await redis_lock.release()
            except Exception:
                await redis_client.invalidate()


coordination = Coordination()
