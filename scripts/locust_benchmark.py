"""Locust scenarios for the work-order platform.

Steady-state traffic reuses tokens from on_start so login CPU is not mixed into
business percentiles. Request names are stable, so Locust reports per endpoint.

Run examples (from repo root, API already up):

  # smoke
  locust -f scripts/locust_benchmark.py --host http://127.0.0.1:8000 --headless -u 5 -r 5 -t 30s --only-summary

  # load
  locust -f scripts/locust_benchmark.py --host http://127.0.0.1:8000 --headless -u 50 -r 10 -t 3m --csv reports/load-50 --html reports/load-50.html

  # stress
  locust -f scripts/locust_benchmark.py --host http://127.0.0.1:8000 --headless -u 100 -r 20 -t 3m --csv reports/load-100 --html reports/load-100.html
"""

from __future__ import annotations

from uuid import uuid4

from locust import HttpUser, between, task
from locust.clients import ResponseContextManager


def _ok(response: ResponseContextManager, *success_codes: int) -> None:
    if response.status_code in success_codes:
        response.success()
        return
    response.failure(f"{response.status_code} {response.text[:160]}")


class PlatformUser(HttpUser):
    """Mixed resident / worker / admin traffic against FastAPI."""

    wait_time = between(0.5, 1.5)

    def on_start(self) -> None:
        self.resident = self._login("resident", "resident123")
        self.worker = self._login("worker", "worker123")
        self.admin = self._login("admin", "admin123")

    def _login(self, username: str, password: str) -> dict[str, str]:
        with self.client.post(
            "/api/v1/resident/auth/login",
            json={"username": username, "password": password},
            name="auth.login",
            catch_response=True,
        ) as response:
            _ok(response, 200)
            token = response.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def _create_order(self) -> int | None:
        payload = {
            "title": "北门路灯无法点亮",
            "description": "园区北门路灯连续闪烁后熄灭，存在夜间通行隐患",
            "area": "全园区",
            "request_id": f"load-{uuid4().hex}",
        }
        with self.client.post(
            "/api/v1/resident/work-orders",
            json=payload,
            headers=self.resident,
            name="resident.create_order",
            catch_response=True,
        ) as response:
            _ok(response, 202)
            if response.status_code != 202:
                return None
            return int(response.json()["data"]["id"])

    @task(5)
    def resident_list(self) -> None:
        with self.client.get(
            "/api/v1/resident/work-orders",
            headers=self.resident,
            name="resident.list_orders",
            catch_response=True,
        ) as response:
            _ok(response, 200)

    @task(2)
    def create_order(self) -> None:
        self._create_order()

    @task(2)
    def admin_read_path(self) -> None:
        with self.client.get(
            "/api/v1/admin/work-orders?page=1&page_size=20",
            headers=self.admin,
            name="admin.list_orders",
            catch_response=True,
        ) as response:
            _ok(response, 200)
        with self.client.get(
            "/api/v1/admin/stats/overview",
            headers=self.admin,
            name="admin.stats_overview",
            catch_response=True,
        ) as response:
            _ok(response, 200)

    @task(2)
    def worker_read_path(self) -> None:
        with self.client.get(
            "/api/v1/worker/work-orders",
            headers=self.worker,
            name="worker.list_assigned",
            catch_response=True,
        ) as response:
            _ok(response, 200)
        with self.client.get(
            "/api/v1/worker/personal/performance",
            headers=self.worker,
            name="worker.performance",
            catch_response=True,
        ) as response:
            _ok(response, 200)

    @task(1)
    def closed_loop(self) -> None:
        order_id = self._create_order()
        if not order_id:
            return
        with self.client.post(
            f"/api/v1/admin/work-orders/{order_id}/dispatch",
            json={"force": False},
            headers=self.admin,
            name="admin.dispatch",
            catch_response=True,
        ) as response:
            if response.status_code == 409:
                response.success()
                return
            _ok(response, 200)
            if response.status_code != 200:
                return
        for status in ("已接单", "处理中", "待回访", "已完成"):
            with self.client.post(
                f"/api/v1/worker/work-orders/{order_id}/status",
                json={"status": status, "detail": f"load-test:{status}"},
                headers=self.worker,
                name=f"worker.transition.{status}",
                catch_response=True,
            ) as response:
                _ok(response, 200)
                if response.status_code != 200:
                    return
        with self.client.post(
            f"/api/v1/resident/work-orders/{order_id}/rating",
            json={"score": 5, "comment": "load-test"},
            headers=self.resident,
            name="resident.rating",
            catch_response=True,
        ) as response:
            _ok(response, 200)

    @task(1)
    def readiness(self) -> None:
        with self.client.get("/health/ready", name="health.ready", catch_response=True) as response:
            _ok(response, 200)
