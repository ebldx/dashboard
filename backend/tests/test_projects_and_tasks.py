from fastapi.testclient import TestClient


def _create_goal(client: TestClient, endpoint: str, title: str) -> dict:
    response = client.post(endpoint, json={"title": title})
    assert response.status_code == 201
    return response.json()


def test_project_goal_milestone_task_progress_and_lifecycle(client: TestClient) -> None:
    career_goal = _create_goal(client, "/api/goals/career", "Become a backend engineer")
    academic_goal = _create_goal(client, "/api/goals/academic", "Complete databases course")
    project_response = client.post(
        "/api/projects",
        json={
            "title": "Portfolio API",
            "description": "Build a small portfolio service",
            "career_goal_ids": [career_goal["id"]],
            "academic_goal_ids": [academic_goal["id"]],
        },
    )
    assert project_response.status_code == 201
    project = project_response.json()
    assert project["career_goal_titles"] == ["Become a backend engineer"]
    assert project["academic_goal_titles"] == ["Complete databases course"]
    assert project["progress_percent"] == 0

    milestone_response = client.post(
        f"/api/projects/{project['id']}/milestones",
        json={"title": "API foundation"},
    )
    assert milestone_response.status_code == 201
    milestone = milestone_response.json()
    task_response = client.post(
        "/api/tasks",
        json={
            "title": "Create database models",
            "category": "projects",
            "project_id": project["id"],
            "milestone_id": milestone["id"],
            "career_goal_id": career_goal["id"],
        },
    )
    assert task_response.status_code == 201
    task = task_response.json()
    assert task["project_title"] == "Portfolio API"
    assert task["milestone_title"] == "API foundation"
    assert task["career_goal_title"] == "Become a backend engineer"
    assert task["completed_at"] is None

    completed_task = client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "completed"},
    )
    assert completed_task.status_code == 200
    assert completed_task.json()["completed_at"] is not None
    progress = client.get(f"/api/projects/{project['id']}").json()
    assert progress["progress_percent"] == 50
    assert progress["completed_task_count"] == 1

    completed_milestone = client.patch(
        f"/api/projects/{project['id']}/milestones/{milestone['id']}",
        json={"status": "completed"},
    )
    assert completed_milestone.status_code == 200
    assert completed_milestone.json()["completed_at"] is not None
    assert client.get(f"/api/projects/{project['id']}").json()["progress_percent"] == 100

    reopened = client.patch(f"/api/tasks/{task['id']}", json={"status": "todo"})
    assert reopened.status_code == 200
    assert reopened.json()["completed_at"] is None
    assert client.get(f"/api/projects/{project['id']}").json()["progress_percent"] == 50


def test_task_filters_and_invalid_goal_or_milestone_links(client: TestClient) -> None:
    project_one = client.post("/api/projects", json={"title": "First project"}).json()
    project_two = client.post("/api/projects", json={"title": "Second project"}).json()
    milestone = client.post(
        f"/api/projects/{project_one['id']}/milestones",
        json={"title": "First milestone"},
    ).json()
    created = client.post(
        "/api/tasks",
        json={
            "title": "Review SQL notes",
            "description": "Prepare for the database exam",
            "category": "academic",
            "priority": "high",
            "project_id": project_one["id"],
            "milestone_id": milestone["id"],
        },
    )
    assert created.status_code == 201
    client.post("/api/tasks", json={"title": "Tidy workspace", "category": "personal"})

    assert len(client.get("/api/tasks", params={"search": "database"}).json()) == 1
    assert len(client.get("/api/tasks", params={"category": "academic"}).json()) == 1
    assert len(client.get("/api/tasks", params={"project_id": project_one["id"]}).json()) == 1
    assert len(client.get("/api/tasks", params={"priority": "high"}).json()) == 1

    wrong_project = client.post(
        "/api/tasks",
        json={
            "title": "Invalid link",
            "project_id": project_two["id"],
            "milestone_id": milestone["id"],
        },
    )
    assert wrong_project.status_code == 422
    invalid_goal = client.post(
        "/api/projects",
        json={"title": "Invalid goal link", "career_goal_ids": ["not-owned"]},
    )
    assert invalid_goal.status_code == 422


def test_deleting_project_or_milestone_preserves_tasks_without_links(
    client: TestClient,
) -> None:
    project = client.post("/api/projects", json={"title": "Delete me"}).json()
    milestone = client.post(
        f"/api/projects/{project['id']}/milestones",
        json={"title": "Keep task"},
    ).json()
    task = client.post(
        "/api/tasks",
        json={
            "title": "Keep this task",
            "project_id": project["id"],
            "milestone_id": milestone["id"],
        },
    ).json()

    deleted_milestone = client.delete(
        f"/api/projects/{project['id']}/milestones/{milestone['id']}"
    )
    assert deleted_milestone.status_code == 204
    task_after_milestone_delete = client.get(f"/api/tasks/{task['id']}").json()
    assert task_after_milestone_delete["project_id"] == project["id"]
    assert task_after_milestone_delete["milestone_id"] is None

    deleted_project = client.delete(f"/api/projects/{project['id']}")
    assert deleted_project.status_code == 204
    task_after_project_delete = client.get(f"/api/tasks/{task['id']}").json()
    assert task_after_project_delete["project_id"] is None
    assert task_after_project_delete["milestone_id"] is None
    assert client.get(f"/api/projects/{project['id']}").status_code == 404


def test_project_rejects_reversed_date_range(client: TestClient) -> None:
    response = client.post(
        "/api/projects",
        json={
            "title": "Bad dates",
            "start_date": "2027-05-01",
            "target_date": "2027-04-30",
        },
    )
    assert response.status_code == 422
