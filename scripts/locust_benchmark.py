from locust import HttpUser, between, task


class WorkOrderUser(HttpUser):
    wait_time = between(0.5, 2)
    token = None

    def on_start(self):
        response = self.client.post("/api/v1/resident/auth/login", json={"username": "resident", "password": "resident123"})
        self.token = response.json()["data"]["access_token"]

    @task(3)
    def list_orders(self):
        self.client.get("/api/v1/resident/work-orders", headers={"Authorization": f"Bearer {self.token}"})

    @task(1)
    def create_order(self):
        self.client.post("/api/v1/resident/work-orders", json={"title": "压测工单", "description": "路灯无法正常点亮", "area": "北区 · 1 号门"}, headers={"Authorization": f"Bearer {self.token}"})
