import pytest

from src.common.cache import MultiLevelCache
from src.core.runtime import validate_runtime_settings


class _Config:
    def __init__(self, environment: str, secret_key: str, database_url: str):
        self.environment = environment
        self.secret_key = secret_key
        self.database_url = database_url


@pytest.mark.asyncio
async def test_multilevel_cache_hits_l1_after_loader():
    layer = MultiLevelCache(namespace="test-cache")
    calls = 0

    async def loader():
        nonlocal calls
        calls += 1
        return {"items": 3}

    first = await layer.get_or_set("stats", loader)
    second = await layer.get_or_set("stats", loader)
    assert first == second == {"items": 3}
    assert calls == 1
    await layer.delete("stats")
    third = await layer.get_or_set("stats", loader)
    assert third == {"items": 3}
    assert calls == 2


@pytest.mark.asyncio
async def test_get_or_set_singleflight_loads_once():
    import asyncio

    layer = MultiLevelCache(namespace="test-singleflight")
    calls = 0
    started = asyncio.Event()
    release = asyncio.Event()

    async def loader():
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return {"n": calls}

    first = asyncio.create_task(layer.get_or_set("hot", loader))
    await started.wait()
    waiters = [asyncio.create_task(layer.get_or_set("hot", loader)) for _ in range(8)]
    release.set()
    results = [await first, *await asyncio.gather(*waiters)]
    assert calls == 1
    assert results == [{"n": 1}] * 9
    await layer.delete("hot")


@pytest.mark.asyncio
async def test_apply_invalidation_clears_local_l1():
    layer = MultiLevelCache(namespace="test-invalidate")
    layer.l1.set("stats", {"items": 1}, 30)
    await layer.apply_invalidation({"keys": ["stats"]})
    assert layer.l1.get("stats") is None
    layer.l1.set("users:list:all", [1], 30)
    await layer.apply_invalidation({"prefix": "users:list:"})
    assert layer.l1.get("users:list:all") is None


def test_jitter_ttl_stays_in_band_and_spreads():
    from src.common.cache import jitter_ttl

    samples = {jitter_ttl(30, 0.2) for _ in range(80)}
    assert samples <= set(range(24, 37))
    assert len(samples) > 1
    assert jitter_ttl(1) == 1


def test_production_runtime_rejects_unsafe_defaults():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_runtime_settings(_Config("production", "change-me-in-production", "postgresql+asyncpg://lingshu:lingshu@db/lingshu"))
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        validate_runtime_settings(_Config("production", "x" * 32, "sqlite+aiosqlite:///./data/lingshu.db"))
    validate_runtime_settings(_Config("production", "x" * 32, "postgresql+asyncpg://lingshu:lingshu@db/lingshu"))
    validate_runtime_settings(_Config("development", "change-me-in-production", "sqlite+aiosqlite:///./data/lingshu.db"))
