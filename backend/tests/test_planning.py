from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from icalendar import Calendar, Event

from app.services import calendar_sync
from app.services.calendar_sync import DownloadedFeed
from app.db.models import Task
from app.services.planning import _score_task

OSLO = ZoneInfo("Europe/Oslo")


def _feed_with_overlapping_events() -> bytes:
    calendar = Calendar()
    calendar.add("prodid", "-//Daymark planning test//EN")
    calendar.add("version", "2.0")
    start = datetime.now(OSLO).replace(hour=10, minute=0, second=0, microsecond=0)
    for uid, title, offset in (
        ("planning-event-1", "Focus block", 0),
        ("planning-event-2", "Study session", 30),
    ):
        event = Event()
        event.add("uid", uid)
        event.add("dtstart", start + timedelta(minutes=offset))
        event.add("dtend", start + timedelta(minutes=offset + 60))
        event.add("summary", title)
        calendar.add_component(event)
    return calendar.to_ical()


def test_planning_prioritizes_urgent_deadlines_and_recommends_active_projects(
    client: TestClient,
) -> None:
    today = datetime.now(OSLO).date()
    project = client.post(
        "/api/projects",
        json={"title": "Build portfolio", "importance": 5, "target_date": (today + timedelta(days=3)).isoformat()},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    due_today = client.post(
        "/api/tasks",
        json={
            "title": "Submit project outline",
            "deadline": today.isoformat(),
            "project_id": project_id,
            "priority": "normal",
        },
    )
    overdue = client.post(
        "/api/tasks",
        json={
            "title": "Review application",
            "deadline": (today - timedelta(days=1)).isoformat(),
            "priority": "high",
        },
    )
    completed = client.post(
        "/api/tasks",
        json={"title": "Already finished", "status": "completed"},
    )
    assert due_today.status_code == overdue.status_code == completed.status_code == 201

    response = client.get("/api/ai/planning")

    assert response.status_code == 200
    plan = response.json()
    assert [item["task_id"] for item in plan["priorities"][:2]] == [
        overdue.json()["id"],
        due_today.json()["id"],
    ]
    assert "Overdue by 1 day(s)" in plan["priorities"][0]["reasons"]
    assert "Due today" in plan["priorities"][1]["reasons"]
    assert plan["priorities"][0]["score"] > plan["priorities"][1]["score"]
    assert completed.json()["id"] not in [item["task_id"] for item in plan["priorities"]]
    assert plan["project_recommendations"][0]["project_id"] == project_id
    assert "Importance 5 of 5" in plan["project_recommendations"][0]["reasons"]


def test_schedule_analysis_merges_overlaps_and_labels_calendar_gaps(
    client: TestClient,
    monkeypatch,
) -> None:
    source = client.patch(
        "/api/calendar/source",
        json={"feed_url": "https://calendar.example.test/planning.ics"},
    )
    assert source.status_code == 200
    monkeypatch.setattr(
        calendar_sync,
        "_download_feed",
        lambda _source: DownloadedFeed(
            _feed_with_overlapping_events(),
            '"planning-etag"',
            None,
        ),
    )
    assert client.post("/api/calendar/sync").status_code == 200

    response = client.get("/api/ai/planning")

    assert response.status_code == 200
    schedule = response.json()["schedule"]
    assert schedule["event_count"] == 2
    assert schedule["events_truncated"] is False
    assert schedule["overlapping_event_count"] == 2
    assert schedule["scheduled_minutes"] == 90
    assert len(schedule["calendar_gaps"]) == 2
    assert sum(gap["duration_minutes"] for gap in schedule["calendar_gaps"]) == 1350


def test_task_scores_explain_alignment_with_active_goals() -> None:
    today = datetime.now(OSLO).date()
    task = Task(
        id="task-1",
        title="Prepare assignment",
        status="todo",
        priority="normal",
        deadline=today,
        career_goal_id="goal-1",
        academic_goal_id=None,
        project_id=None,
        estimated_duration_minutes=45,
    )

    aligned = _score_task(task, today, {"goal-1"}, {})
    not_aligned = _score_task(task, today, set(), {})

    assert aligned.score == not_aligned.score + 15
    assert "Supports an active goal" in aligned.reasons
    assert "Supports an active goal" not in not_aligned.reasons
