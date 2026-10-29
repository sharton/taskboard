def test_home_page_empty(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_home_page_shows_tasks(client, create_task):
    create_task(title="Visible on board")

    response = client.get("/")

    assert response.status_code == 200
    assert "Visible on board" in response.text


def test_static_css_served(client):
    response = client.get("/static/styles.css")

    assert response.status_code == 200


def test_create_task_from_form(client):
    response = client.post(
        "/tasks",
        data={"title": "  From form  ", "description": "  trimmed  "},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    task = client.get("/api/tasks").json()[0]
    assert task["title"] == "From form"
    assert task["description"] == "trimmed"


def test_edit_page(client, create_task):
    task = create_task(title="Editable")

    response = client.get(f"/tasks/{task['id']}/edit")

    assert response.status_code == 200
    assert "Editable" in response.text


def test_edit_page_not_found(client):
    response = client.get("/tasks/999/edit")

    assert response.status_code == 404


def test_update_task_from_form(client, create_task):
    task = create_task(title="Before")

    response = client.post(
        f"/tasks/{task['id']}/edit",
        data={"title": "After", "description": "Updated", "status": "in_progress"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    updated = client.get(f"/api/tasks/{task['id']}").json()
    assert updated["title"] == "After"
    assert updated["description"] == "Updated"
    assert updated["status"] == "in_progress"


def test_update_status_from_form(client, create_task):
    task = create_task()

    response = client.post(
        f"/tasks/{task['id']}/status",
        data={"status": "done"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert client.get(f"/api/tasks/{task['id']}").json()["status"] == "done"


def test_update_status_from_form_not_found(client):
    response = client.post("/tasks/999/status", data={"status": "done"}, follow_redirects=False)

    assert response.status_code == 404


def test_delete_task_from_form(client, create_task):
    task = create_task()

    response = client.post(f"/tasks/{task['id']}/delete", follow_redirects=False)

    assert response.status_code == 303
    assert client.get("/api/tasks").json() == []
