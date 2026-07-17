from uuid import uuid4

from fastapi.testclient import TestClient

from main import app


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/resident/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_create_and_dispatch_work_order():
    with TestClient(app) as client:
        resident_token = _login(client, "resident", "resident123")
        created = client.post(
            "/api/v1/resident/work-orders",
            headers={"Authorization": f"Bearer {resident_token}", "X-Trace-ID": "test-flow"},
            json={
                "title": "B2 办公区空调不制冷",
                "description": "会议室空调无法制冷，室温持续升高",
                "area": "全园区",
                "request_id": f"test-{uuid4().hex}",
            },
        )
        assert created.status_code == 202, created.text
        order = created.json()["data"]
        assert order["category"] == "暖通空调"
        assert order["status"] == "待派单"

        admin_token = _login(client, "admin", "admin123")
        dispatched = client.post(
            f"/api/v1/admin/work-orders/{order['id']}/dispatch",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"force": False},
        )
        assert dispatched.status_code == 200, dispatched.text
        assert dispatched.json()["data"]["work_order"]["status"] == "已派单"
        assert dispatched.json()["data"]["decision"]["worker_name"] == "李昂"
