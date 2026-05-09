from locust import HttpUser, task, between
import uuid


class TaskManagerUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        self.username = f"user_{uuid.uuid4().hex[:8]}"

        # 注册（加超时处理）
        with self.client.post("/auth/register", json={
            "username": self.username,
            "password": "123456"
        }, catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"注册失败: {resp.status_code}")
                return

        # 登录（加超时处理）
        with self.client.post("/auth/login", json={
            "username": self.username,
            "password": "123456"
        }, catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"登录失败: {resp.status_code}")
                return
            try:
                self.token = resp.json().get("access_token")
                self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            except Exception as e:
                resp.failure(f"解析token失败: {e}")

    @task(2)
    def get_tasks(self):
        self.client.get("/tasks")

    @task(1)
    def create_task(self):
        self.client.post("/tasks", json={
            "title": "压测任务",
            "description": "测试系统性能"
        })

