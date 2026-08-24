import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("MEDIA_STORAGE_MODE", "local")
os.environ.setdefault("CIRCUIT_FAILURE_THRESHOLD", "5")
os.environ.setdefault("CIRCUIT_RECOVERY_SECONDS", "30")
os.environ.setdefault("AI_ASYNC_ENABLED", "false")


import pytest

from src.common.cache import cache
from src.common.circuit_breaker import circuits


@pytest.fixture(autouse=True)
def reset_circuits():
    circuits.reset()
    cache.l1.clear()
    yield
    circuits.reset()
    cache.l1.clear()


@pytest.fixture(autouse=True)
def disable_redis(monkeypatch):
    async def unavailable(*_args, **_kwargs):
        raise ConnectionError("redis disabled in tests")

    monkeypatch.setattr("src.extensions.redis_client.RedisClient.connect", unavailable)
