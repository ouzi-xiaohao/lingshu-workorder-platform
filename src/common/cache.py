from __future__ import annotations

import asyncio
import json
import random
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from src.common.circuit_breaker import circuits
from src.common.local_cache import LocalTTLCache
from src.core.config import settings
from src.extensions.redis_client import redis_client


T = TypeVar("T")
_MISS = object()
INVALIDATE_CHANNEL = "lingshu:cache:invalidate"


def jitter_ttl(ttl: int, ratio: float | None = None) -> int:
    """Spread expiry so neighbouring keys are less likely to collapse together."""
    if ttl <= 1:
        return ttl
    spread = max(1, int(ttl * (settings.cache_ttl_jitter_ratio if ratio is None else ratio)))
    return max(1, ttl + random.randint(-spread, spread))


class MultiLevelCache:
    """L1 process memory plus L2 Redis. Redis outages fall back to L1 then the loader."""

    def __init__(self, namespace: str = "lingshu:cache"):
        self.namespace = namespace
        self.l1 = LocalTTLCache(max_items=settings.cache_max_l1_items)
        self._inflight: dict[str, asyncio.Future[Any]] = {}

    def _l1_ttl(self, ttl: int) -> int:
        return max(1, min(settings.cache_l1_ttl_seconds, ttl))

    def _redis_key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    async def get_or_set(self, key: str, loader: Callable[[], Awaitable[T]], ttl: int | None = None) -> T:
        ttl = ttl or settings.cache_l2_ttl_seconds
        cached = await self.get(key)
        if cached is not _MISS:
            return cached
        pending = self._inflight.get(key)
        if pending is not None:
            return await asyncio.shield(pending)
        future: asyncio.Future[T] = asyncio.get_running_loop().create_future()
        self._inflight[key] = future
        try:
            value = await loader()
            await self.set(key, value, ttl)
            future.set_result(value)
            return value
        except Exception as exc:
            future.set_exception(exc)
            raise
        finally:
            if self._inflight.get(key) is future:
                self._inflight.pop(key, None)

    async def get(self, key: str) -> Any:
        hit, local = self.l1.lookup(key)
        if hit:
            return local
        remote = await self._get_l2(key)
        if remote is not _MISS:
            self.l1.set(key, remote, self._l1_ttl(jitter_ttl(settings.cache_l1_ttl_seconds)))
            return remote
        return _MISS

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = jitter_ttl(ttl or settings.cache_l2_ttl_seconds)
        self.l1.set(key, value, self._l1_ttl(jitter_ttl(settings.cache_l1_ttl_seconds)))
        await self._set_l2(key, value, ttl)

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self.l1.delete(key)
            await self._delete_l2(key)
        await self._publish_invalidation(keys=list(keys))

    async def delete_prefix(self, prefix: str) -> None:
        self.l1.delete_prefix(prefix)
        await self._delete_l2_prefix(prefix)
        await self._publish_invalidation(prefix=prefix)

    async def _get_l2(self, key: str) -> Any:
        breaker = circuits.get("redis")
        if not breaker.allow_request():
            return _MISS
        try:
            client = await redis_client.connect()
            raw = await client.get(self._redis_key(key))
            breaker.record_success()
            if raw is None:
                return _MISS
            return json.loads(raw)
        except Exception:
            breaker.record_failure()
            await redis_client.invalidate()
            return _MISS

    async def _set_l2(self, key: str, value: Any, ttl: int) -> None:
        breaker = circuits.get("redis")
        if not breaker.allow_request():
            return
        try:
            client = await redis_client.connect()
            await client.set(self._redis_key(key), json.dumps(value, ensure_ascii=False, default=str), ex=ttl)
            breaker.record_success()
        except Exception:
            breaker.record_failure()
            await redis_client.invalidate()

    async def _delete_l2(self, key: str) -> None:
        breaker = circuits.get("redis")
        if not breaker.allow_request():
            return
        try:
            client = await redis_client.connect()
            await client.delete(self._redis_key(key))
            breaker.record_success()
        except Exception:
            breaker.record_failure()
            await redis_client.invalidate()

    async def _delete_l2_prefix(self, prefix: str) -> None:
        breaker = circuits.get("redis")
        if not breaker.allow_request():
            return
        try:
            client = await redis_client.connect()
            async for redis_key in client.scan_iter(match=f"{self.namespace}:{prefix}*"):
                await client.delete(redis_key)
            breaker.record_success()
        except Exception:
            breaker.record_failure()
            await redis_client.invalidate()

    async def _publish_invalidation(self, keys: list[str] | None = None, prefix: str | None = None) -> None:
        breaker = circuits.get("redis")
        if not breaker.allow_request():
            return
        try:
            client = await redis_client.connect()
            await client.publish(INVALIDATE_CHANNEL, json.dumps({"keys": keys or [], "prefix": prefix}))
            breaker.record_success()
        except Exception:
            breaker.record_failure()
            await redis_client.invalidate()

    async def apply_invalidation(self, payload: dict[str, Any]) -> None:
        for key in payload.get("keys") or []:
            self.l1.delete(str(key))
        prefix = payload.get("prefix")
        if prefix:
            self.l1.delete_prefix(str(prefix))

    async def listen_invalidations(self) -> None:
        breaker = circuits.get("redis")
        if not breaker.allow_request():
            return
        try:
            client = await redis_client.connect()
            pubsub = client.pubsub()
            await pubsub.subscribe(INVALIDATE_CHANNEL)
            breaker.record_success()
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                raw = message.get("data")
                if not raw:
                    continue
                payload = json.loads(raw if isinstance(raw, str) else raw.decode())
                await self.apply_invalidation(payload)
        except Exception:
            breaker.record_failure()
            await redis_client.invalidate()


cache = MultiLevelCache()
STATS_KEY = "stats:overview"
CONFIGS_KEY = "system:configs"
USERS_PREFIX = "users:list:"
WORKER_PERF_PREFIX = "worker:performance:"


async def invalidate_stats() -> None:
    await cache.delete(STATS_KEY)


async def invalidate_users() -> None:
    await cache.delete_prefix(USERS_PREFIX)


async def invalidate_worker(user_id: int | None = None) -> None:
    await invalidate_stats()
    if user_id is None:
        await cache.delete_prefix(WORKER_PERF_PREFIX)
        return
    await cache.delete(f"{WORKER_PERF_PREFIX}{user_id}")
