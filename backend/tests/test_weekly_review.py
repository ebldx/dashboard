from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app.services import daily_briefing
from app.services.weekly_review import last_complete_week_start


def _settings(
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        ollama_base_url=base_url,
        ollama_model=model,
        ollama_timeout_seconds=5,
    )


def test_weekly_review_has_offline_fallback_and_manual_retry_bypasses_backoff(
    client: TestClient,
    monkeypatch,
) -> None:
    week_start = date(2024, 1, 1)
    monkeypatch.setattr(
        daily_briefing,
        "get_settings",
        lambda: _settings(),
    )

    offline = client.get(
        "/api/ai/weekly-review",
        params={"week_start": week_start.isoformat()},
    )

    assert offline.status_code == 200
    fallback = offline.json()
    assert fallback["generation_status"] == "pending"
    assert fallback["attempt_count"] == 1
    assert fallback["stats"]["tasks_created"] == 0
    assert fallback["content"]["summary"] == (
        "There is limited recorded task and calendar activity for this week."
    )
    assert fallback["next_retry_at"] is not None

    observed_context: dict[str, Any] = {}

    class FakeOllama:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def generate_json(self, **kwargs: Any) -> dict[str, Any]:
            observed_context.update(kwargs["context"])
            return {
                "summary": "A calm week with room to choose what comes next.",
                "wins": [],
                "reflection_question": "What felt worthwhile?",
                "suggested_focus": ["Choose one priority."],
            }

    monkeypatch.setattr(
        daily_briefing,
        "get_settings",
        lambda: _settings(base_url="http://ollama.example.test:11434", model="test-model"),
    )
    monkeypatch.setattr(daily_briefing, "OllamaClient", FakeOllama)

    retried = client.post(
        "/api/ai/weekly-review/retry",
        params={"week_start": week_start.isoformat()},
    )

    assert retried.status_code == 200
    assert retried.json()["generation_status"] == "generated"
    assert retried.json()["attempt_count"] == 2
    assert observed_context["week_start"] == week_start.isoformat()
    assert set(observed_context["statistics"]) == {
        "tasks_created",
        "tasks_completed",
        "tasks_with_deadlines",
        "calendar_events",
        "scheduled_minutes",
        "feedback_count",
        "helpful_feedback_count",
        "unhelpful_feedback_count",
    }


def test_weekly_review_is_idempotent_and_rejects_incomplete_weeks(
    client: TestClient,
    monkeypatch,
) -> None:
    calls = 0

    class FakeOllama:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def generate_json(self, **_kwargs: Any) -> dict[str, Any]:
            nonlocal calls
            calls += 1
            return {
                "summary": "A grounded weekly summary.",
                "wins": [],
                "reflection_question": "What would you repeat?",
                "suggested_focus": [],
            }

    monkeypatch.setattr(
        daily_briefing,
        "get_settings",
        lambda: _settings(base_url="http://ollama.example.test:11434", model="test-model"),
    )
    monkeypatch.setattr(daily_briefing, "OllamaClient", FakeOllama)
    week_start = last_complete_week_start()

    first = client.get(
        "/api/ai/weekly-review",
        params={"week_start": week_start.isoformat()},
    )
    second = client.get(
        "/api/ai/weekly-review",
        params={"week_start": week_start.isoformat()},
    )
    incomplete = client.get(
        "/api/ai/weekly-review",
        params={"week_start": (week_start + timedelta(days=7)).isoformat()},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert calls == 1
    assert incomplete.status_code == 422
