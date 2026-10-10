from locust import HttpUser, task, between


class GraphRAGUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(3)
    def ask_simple_lookup(self):
        self.client.post(
            "/v1/ask",
            json={
                "question": "Where is Acme Corp located?",
                "max_hops": 3,
                "lang": "en",
            },
        )

    @task(2)
    def ask_multi_hop(self):
        self.client.post(
            "/v1/ask",
            json={
                "question": "Who leads the GraphRAG System project at Acme Corp?",
                "max_hops": 3,
                "lang": "en",
            },
        )

    @task(1)
    def check_health(self):
        self.client.get("/healthz")
