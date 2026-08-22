from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from main import app
from src.common.circuit_breaker import CircuitState, circuits


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_ready_depends_on_database():
    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 200
        body = response.json()
        assert body["checks"]["database"] == "ok"
        assert body["status"] in {"ok", "degraded"}
        assert "redis" in body["checks"]


def test_ready_skips_redis_when_circuit_open():
    breaker = circuits.get("redis")
    breaker.failure_threshold = 1
    breaker.record_failure()
    assert breaker.state is CircuitState.OPEN
    with TestClient(app) as client:
        with patch("src.app.redis_client.connect", new_callable=AsyncMock) as connect:
            response = client.get("/health/ready")
            assert response.status_code == 200
            assert response.json()["checks"]["redis"] == "unavailable"
            assert response.json()["status"] == "degraded"
            connect.assert_not_called()


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_ready_depends_on_database():
    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 200
        body = response.json()
        assert body["checks"]["database"] == "ok"
        assert body["status"] in {"ok", "degraded"}
        assert "redis" in body["checks"]
