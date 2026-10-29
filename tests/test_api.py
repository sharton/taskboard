import pytest

from app.config import settings


def test_healthcheck(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": settings.app_name}


def test_list_tasks_empty(client):
    response = client.get("/api/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_create_task(client):
    response = client.post(
        "/api/tasks",
        json={"title": "Prepare server", "description": "Install Docker"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["title"] == "Prepare server"
    assert data["description"] == "Install Docker"
    assert data["status"] == "new"
    assert data["created_at"]
    assert data["updated_at"]


def test_create_task_with_status(create_task):
    task = create_task(title="Already started", status="in_progress")

    assert task["status"] == "in_progress"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": ""},
        {"title": "x" * 201},
        {"title": "ok", "description": "x" * 5001},
        {"title": "ok", "status": "unknown"},
    ],
)
def test_create_task_validation(client, payload):
    response = client.post("/api/tasks", json=payload)

    assert response.status_code == 422


def test_list_tasks_newest_first(client, create_task):
    first = create_task(title="First")
    second = create_task(title="Second")

    ids = [task["id"] for task in client.get("/api/tasks").json()]

    assert ids == [second["id"], first["id"]]


def test_get_task(client, create_task):
    task = create_task(title="Read me")

    response = client.get(f"/api/tasks/{task['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Read me"


def test_get_task_not_found(client):
    response = client.get("/api/tasks/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_update_task(client, create_task):
    task = create_task(title="Old", description="Old description")

    response = client.put(
        f"/api/tasks/{task['id']}",
        json={"title": "New", "status": "done"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New"
    assert data["status"] == "done"
    # Поля, которые не передали, не должны меняться.
    assert data["description"] == "Old description"


def test_update_task_not_found(client):
    response = client.put("/api/tasks/999", json={"title": "New"})

    assert response.status_code == 404


def test_update_task_validation(client, create_task):
    task = create_task()

    response = client.put(f"/api/tasks/{task['id']}", json={"title": ""})

    assert response.status_code == 422


@pytest.mark.parametrize("new_status", ["new", "in_progress", "done"])
def test_update_task_status(client, create_task, new_status):
    task = create_task()

    response = client.patch(f"/api/tasks/{task['id']}/status", json={"status": new_status})

    assert response.status_code == 200
    assert response.json()["status"] == new_status


def test_update_task_status_invalid(client, create_task):
    task = create_task()

    response = client.patch(f"/api/tasks/{task['id']}/status", json={"status": "archived"})

    assert response.status_code == 422


def test_update_task_status_not_found(client):
    response = client.patch("/api/tasks/999/status", json={"status": "done"})

    assert response.status_code == 404


def test_delete_task(client, create_task):
    task = create_task()

    response = client.delete(f"/api/tasks/{task['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/tasks/{task['id']}").status_code == 404


def test_delete_task_not_found(client):
    response = client.delete("/api/tasks/999")

    assert response.status_code == 404
