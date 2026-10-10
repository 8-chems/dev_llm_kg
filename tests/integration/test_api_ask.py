import pytest
from fastapi.testclient import TestClient
from src.app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ask_endpoint_happy_path(client):
    payload = {
        "question": "Where is Acme Corp located?",
        "max_hops": 3,
        "lang": "en",
    }
    response = client.post("/v1/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert "trace" in data
    assert data["mode"] in ["off", "shadow", "live"]


def test_admin_flags(client):
    res = client.get("/v1/admin/flags")
    assert res.status_code == 200
    assert "resolve" in res.json()

    put_res = client.put(
        "/v1/admin/flags",
        json={"decision": "resolve", "mode": "shadow", "tau": 0.88},
    )
    assert put_res.status_code == 200
    assert put_res.json()["tau"] == 0.88


def test_review_tasks(client):
    res = client.get("/v1/review/tasks")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
