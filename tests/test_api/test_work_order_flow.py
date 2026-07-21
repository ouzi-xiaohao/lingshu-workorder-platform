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

        for status in ("已接单", "处理中", "待回访", "已完成"):
            transitioned = client.post(
                f"/api/v1/worker/work-orders/{order['id']}/status",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"status": status, "detail": f"测试流转至{status}"},
            )
            assert transitioned.status_code == 200, transitioned.text
            assert transitioned.json()["data"]["status"] == status

        rated = client.post(
            f"/api/v1/resident/work-orders/{order['id']}/rating",
            headers={"Authorization": f"Bearer {resident_token}"},
            json={"score": 5, "comment": "处理及时"},
        )
        assert rated.status_code == 200, rated.text


def test_upload_media_and_create_multimodal_order():
    with TestClient(app) as client:
        token = _login(client, "resident", "resident123")
        headers = {"Authorization": f"Bearer {token}"}
        uploaded = client.post(
            "/api/v1/resident/media",
            headers=headers,
            files={"file": ("water-leak.png", b"\x89PNG\r\n\x1a\n" + b"demo", "image/png")},
        )
        assert uploaded.status_code == 201, uploaded.text
        attachment = uploaded.json()["data"]
        assert attachment["media_type"] == "image"
        assert attachment["sha256"]

        created = client.post(
            "/api/v1/resident/work-orders",
            headers=headers,
            json={
                "title": "地下车库出现积水",
                "description": "A3 区域地面持续积水，请尽快处理",
                "area": "全园区",
                "request_id": f"media-{uuid4().hex}",
                "attachments": [{key: attachment[key] for key in ("media_type", "object_key", "original_name", "size_bytes")}],
            },
        )
        assert created.status_code == 202, created.text
        order = created.json()["data"]
        assert len(order["attachments"]) == 1
        assert "water" in order["attachments"][0]["detected_features"]
