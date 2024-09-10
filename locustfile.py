from locust import HttpUser, TaskSet, task, between

class UserBehavior(TaskSet):
    
    @task
    def index(self):
        self.client.get("/")

    @task(3)
    def view_task(self):
        self.client.get("/add_task")

    @task(1)
    def logout(self):
        self.client.get("/logout")

    @task
    def login(self):
        self.client.post("/login", {
            "username": "testuser",
            "password": "testpassword"
        })

class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 5)
