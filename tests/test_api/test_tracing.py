import logging
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from src.common.logger import logger


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/resident/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_json_responses_include_trace_id():
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Trace-ID": "health-trace"})
        assert response.status_code == 200
        assert response.headers["x-trace-id"] == "health-trace"
        assert response.json()["trace_id"] == "health-trace"


def test_unauthorized_response_includes_trace_id():
    with TestClient(app) as client:
        response = client.get("/api/v1/resident/work-orders", headers={"X-Trace-ID": "auth-trace"})
        assert response.status_code == 401
        body = response.json()
        assert body["trace_id"] == "auth-trace"
        assert body["code"] == "AUTH_401"
        assert response.headers["x-trace-id"] == "auth-trace"


def test_work_order_lifecycle_can_be_found_by_any_trace(caplog):
    caplog.set_level(logging.INFO, logger=logger.name)
    with TestClient(app) as client:
        resident_token = _login(client, "resident", "resident123")
        created = client.post(
            "/api/v1/resident/work-orders",
            headers={"Authorization": f"Bearer {resident_token}", "X-Trace-ID": "create-trace"},
            json={
                "title": "消防通道被纸箱堵塞",
                "description": "南区消防通道被杂物占用，存在安全隐患",
                "area": "全园区",
                "request_id": f"trace-{uuid4().hex}",
            },
        )
        assert created.status_code == 202, created.text
        order = created.json()["data"]
        assert created.json()["trace_id"] == "create-trace"
        assert order["trace_id"] == "create-trace"
        assert order["events"][0]["trace_id"] == "create-trace"

        admin_token = _login(client, "admin", "admin123")
        dispatched = client.post(
            f"/api/v1/admin/work-orders/{order['id']}/dispatch",
            headers={"Authorization": f"Bearer {admin_token}", "X-Trace-ID": "dispatch-trace"},
            json={"force": False},
        )
        assert dispatched.status_code == 200, dispatched.text
        events = dispatched.json()["data"]["work_order"]["events"]
        assert any(event["action"] == "dispatched" and event["trace_id"] == "dispatch-trace" for event in events)
        assert dispatched.json()["data"]["work_order"]["trace_id"] == "create-trace"

        by_create = client.get(
            "/api/v1/admin/work-orders",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"trace_id": "create-trace"},
        )
        by_dispatch = client.get(
            "/api/v1/admin/work-orders",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"trace_id": "dispatch-trace"},
        )
        assert by_create.status_code == 200
        assert by_dispatch.status_code == 200
        assert any(item["id"] == order["id"] for item in by_create.json()["data"]["items"])
        assert any(item["id"] == order["id"] for item in by_dispatch.json()["data"]["items"])

    messages = [record.getMessage() for record in caplog.records]
    assert "http.request" in messages
    assert "work_order.create.start" in messages
    assert "agent.intent-agent.start" in messages
    assert "work_order.dispatch.start" in messages
    assert any(getattr(record, "root_trace_id", None) == "create-trace" for record in caplog.records)
