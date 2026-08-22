from unittest.mock import AsyncMock, patch

import pytest

from src.ai_services.stt_service import SpeechToTextService
from src.common.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState, circuits
from src.common.redis_tools import Coordination
from src.extensions.minio_client import ObjectStorageClient, ObjectStorageUnavailable
from src.extensions.redis_client import reject_if_redis_open


class Clock:
    def __init__(self, value: float = 0):
        self.value = value

    def __call__(self) -> float:
        return self.value


def test_opens_after_threshold_and_fails_fast():
    clock = Clock()
    breaker = CircuitBreaker("demo", failure_threshold=3, recovery_seconds=10, clock=clock)

    def boom():
        raise RuntimeError("down")

    for _ in range(3):
        with pytest.raises(RuntimeError, match="down"):
            breaker.execute_sync(boom)

    assert breaker.state is CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        breaker.execute_sync(boom)
    assert breaker.execute_sync(boom, lambda: "degraded") == "degraded"


def test_half_open_success_closes_circuit():
    clock = Clock()
    breaker = CircuitBreaker("demo", failure_threshold=2, recovery_seconds=10, half_open_max_calls=1, clock=clock)
    for _ in range(2):
        breaker.execute_sync(lambda: (_ for _ in ()).throw(RuntimeError("down")), lambda: "fb")
    assert breaker.state is CircuitState.OPEN

    clock.value = 10
    assert breaker.execute_sync(lambda: "ok") == "ok"
    assert breaker.state is CircuitState.CLOSED


def test_half_open_failure_opens_again():
    clock = Clock()
    breaker = CircuitBreaker("demo", failure_threshold=2, recovery_seconds=10, clock=clock)
    for _ in range(2):
        breaker.execute_sync(lambda: (_ for _ in ()).throw(RuntimeError("down")), lambda: "fb")
    clock.value = 10
    assert breaker.execute_sync(lambda: (_ for _ in ()).throw(RuntimeError("still down")), lambda: "fb") == "fb"
    assert breaker.state is CircuitState.OPEN


@pytest.mark.asyncio
async def test_async_execute_uses_fallback_when_open():
    breaker = CircuitBreaker("demo", failure_threshold=1, recovery_seconds=30)
    await breaker.execute(lambda: (_ for _ in ()).throw(RuntimeError("down")), lambda: "fb")
    assert await breaker.execute(lambda: "should-not-run", lambda: "degraded") == "degraded"


def test_minio_auto_mode_writes_local_when_primary_fails(tmp_path, monkeypatch):
    from src.core.config import settings

    client = ObjectStorageClient()
    client.local_root = tmp_path
    monkeypatch.setattr(settings, "media_storage_mode", "auto")
    monkeypatch.setattr(client, "_require_client", lambda: (_ for _ in ()).throw(RuntimeError("minio down")))

    key = "users/1/demo.txt"
    assert client.upload_bytes(key, b"hello", "text/plain") == key
    assert (tmp_path / key).read_bytes() == b"hello"
    assert circuits.get("minio").state is CircuitState.CLOSED


def test_minio_forced_mode_opens_and_fails_fast(tmp_path, monkeypatch):
    from src.core.config import settings

    client = ObjectStorageClient()
    client.local_root = tmp_path
    monkeypatch.setattr(settings, "media_storage_mode", "minio")
    monkeypatch.setattr(client, "_require_client", lambda: (_ for _ in ()).throw(RuntimeError("minio down")))
    circuits.get("minio").failure_threshold = 2

    with pytest.raises(ObjectStorageUnavailable):
        client.upload_bytes("users/1/a.txt", b"x", "text/plain")
    with pytest.raises(ObjectStorageUnavailable):
        client.upload_bytes("users/1/b.txt", b"x", "text/plain")
    assert circuits.get("minio").state is CircuitState.OPEN
    with patch.object(client, "_require_client") as connect:
        with pytest.raises(ObjectStorageUnavailable):
            client.upload_bytes("users/1/c.txt", b"x", "text/plain")
        connect.assert_not_called()


@pytest.mark.asyncio
async def test_redis_lock_falls_back_to_local_and_then_skips_redis():
    coordination = Coordination()
    breaker = circuits.get("redis")
    breaker.failure_threshold = 2

    with patch("src.common.redis_tools.redis_client.connect", AsyncMock(side_effect=ConnectionError("redis down"))):
        async with coordination.lock("order-1"):
            held = True
        assert held
        async with coordination.lock("order-2"):
            pass
        assert breaker.state is CircuitState.OPEN
        with patch("src.common.redis_tools.redis_client.connect") as connect:
            async with coordination.lock("order-3"):
                pass
            connect.assert_not_called()


@pytest.mark.asyncio
async def test_stt_degrades_and_stops_calling_model_when_circuit_open(monkeypatch):
    from src.core.config import settings

    monkeypatch.setattr(settings, "ai_mode", "local")
    service = SpeechToTextService()
    circuits.get("ai-stt").failure_threshold = 2
    with patch.object(service, "_transcribe_sync", side_effect=RuntimeError("whisper down")) as transcribe:
        first = await service.transcribe("users/1/audio.wav")
        second = await service.transcribe("users/1/audio.wav")
        third = await service.transcribe("users/1/audio.wav")
        assert transcribe.call_count == 2
    assert first.startswith("音频附件已接收")
    assert second.startswith("音频附件已接收")
    assert third.startswith("音频附件已接收")
    assert circuits.get("ai-stt").state is CircuitState.OPEN


def test_redis_connect_fails_fast_when_circuit_open():
    breaker = circuits.get("redis")
    breaker.failure_threshold = 1
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        reject_if_redis_open()


def test_admin_circuit_snapshot():
    from fastapi.testclient import TestClient

    from main import app

    with TestClient(app) as client:
        token = client.post("/api/v1/resident/auth/login", json={"username": "admin", "password": "admin123"}).json()["data"]["access_token"]
        response = client.get("/api/v1/admin/system/circuits", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200, response.text
        names = {item["name"] for item in response.json()["data"]}
        assert {"minio", "redis", "ai-stt", "ai-vision", "ai-llm", "ai-llm-backup"} <= names
        assert all(item["state"] in {"closed", "open", "half_open"} for item in response.json()["data"])
