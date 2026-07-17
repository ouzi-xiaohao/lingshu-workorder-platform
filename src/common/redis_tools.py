import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from time import monotonic


class LocalCoordinationFallback:
    def __init__(self):
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._cache: dict[str, tuple[float, object]] = {}

    @asynccontextmanager
    async def lock(self, key: str, timeout: float = 5):
        lock = self._locks[key]
        await asyncio.wait_for(lock.acquire(), timeout)
        try:
            yield
        finally:
            lock.release()

    async def get(self, key: str):
        item = self._cache.get(key)
        if not item or item[0] < monotonic():
            self._cache.pop(key, None)
            return None
        return item[1]

    async def set(self, key: str, value: object, ttl: int = 60):
        self._cache[key] = (monotonic() + ttl, value)


coordination = LocalCoordinationFallback()
