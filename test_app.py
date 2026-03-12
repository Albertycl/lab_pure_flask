import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_get_tasks(client):
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_create_task(client):
    resp = client.post("/api/tasks", json={"title": "Test task"})
    assert resp.status_code == 201
    assert resp.get_json()["title"] == "Test task"


def test_create_task_missing_title(client):
    resp = client.post("/api/tasks", json={})
    assert resp.status_code == 400


def test_delete_task(client):
    resp = client.post("/api/tasks", json={"title": "To delete"})
    task_id = resp.get_json()["id"]
    resp = client.delete(f"/api/tasks/{task_id}")
    assert resp.status_code == 200


def test_delete_task_not_found(client):
    resp = client.delete("/api/tasks/9999")
    assert resp.status_code == 404
