from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app.ai.ollama import OllamaError
from app.services import daily_briefing


def _settings(
    *,
    base_url: str | None = "http://ollama.example.test:11434",
    model: str | None = "test-model",
) -> SimpleNamespace:
    return SimpleNamespace(
        ollama_base_url=base_url,
        ollama_model=model,
        ollama_timeout_seconds=5,
    )


def test_ollama_status_is_truthful_when_not_configured(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(daily_briefing, "get_settings", lambda: _settings(base_url=None, model=None))

    response = client.get("/api/ai/status")

    assert response.status_code == 200
    assert response.json() == {
        "configured": False,
        "reachable": False,
        "model_configured": False,
        "model_available": False,
        "model_name": None,
        "status": "not_configured",
    }


def test_briefing_uses_bounded_context_and_validates_references(
    client: TestClient,
    monkeypatch,
) -> None:
    task = client.post(
        "/api/tasks",
        json={
            "title": "Prepare project outline",
            "description": "Do not send this private description to AI.",
            "priority": "high",
        },
    ).json()
    client.post("/api/tasks", json={"title": "Finished task", "status": "completed"})
    observed_context: dict[str, Any] = {}

    class FakeOllama:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def generate_json(self, **kwargs: Any) -> dict[str, Any]:
            observed_context.update(kwargs["context"])
            return {
                "overview": "A focused day starts with one clear next step.",
                "priorities": [{"task_id": task["id"], "reason": "It is a high-priority task."}],
                "principle_reminders": [],
                "focus_advice": "Begin with the outline.",
            }

    monkeypatch.setattr(daily_briefing, "get_settings", _settings)
    monkeypatch.setattr(daily_briefing, "OllamaClient", FakeOllama)

    response = client.get("/api/ai/briefing")

    assert response.status_code == 200
    briefing = response.json()
    assert briefing["generation_status"] == "generated"
    assert briefing["content"]["priorities"][0]["task_title"] == "Prepare project outline"
    assert [item["title"] for item in observed_context["tasks"]] == [
        "Prepare project outline"
    ]
    assert observed_context["planning"]["priorities"][0]["task_id"] == task["id"]
    assert "private description" not in str(observed_context)
    assert "resume" not in observed_context


def test_unavailable_ollama_returns_retryable_fallback(
    client: TestClient,
    monkeypatch,
) -> None:
    class UnavailableOllama:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def generate_json(self, **_kwargs: Any) -> dict[str, Any]:
            raise OllamaError("Ollama failed to generate a briefing")

    monkeypatch.setattr(daily_briefing, "get_settings", _settings)
    monkeypatch.setattr(daily_briefing, "OllamaClient", UnavailableOllama)

    response = client.get("/api/ai/briefing")

    assert response.status_code == 200
    assert response.json()["generation_status"] == "pending"
    assert response.json()["error_message"] == "Ollama failed to generate a briefing"
    assert response.json()["content"]["priorities"] == []


def test_briefing_retry_respects_backoff_until_manual_retry(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        daily_briefing,
        "get_settings",
        lambda: _settings(base_url=None, model=None),
    )

    first = client.get("/api/ai/briefing")
    within_backoff = client.get("/api/ai/briefing")

    assert first.status_code == 200
    assert first.json()["attempt_count"] == 1
    assert first.json()["next_retry_at"] is not None
    assert within_backoff.json()["attempt_count"] == 1

    class AvailableOllama:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def generate_json(self, **_kwargs: Any) -> dict[str, Any]:
            return {
                "overview": "A calm day with one clear priority.",
                "priorities": [],
                "principle_reminders": [],
                "project_recommendations": [],
                "focus_advice": "Choose a manageable next step.",
            }

    monkeypatch.setattr(daily_briefing, "get_settings", _settings)
    monkeypatch.setattr(daily_briefing, "OllamaClient", AvailableOllama)

    manual_retry = client.post("/api/ai/briefing/retry")

    assert manual_retry.status_code == 200
    assert manual_retry.json()["generation_status"] == "generated"
    assert manual_retry.json()["attempt_count"] == 2


def test_invalid_model_output_is_not_persisted_as_generated(
    client: TestClient,
    monkeypatch,
) -> None:
    class InvalidOllama:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def generate_json(self, **_kwargs: Any) -> dict[str, Any]:
            return {"overview": "Missing required fields"}

    monkeypatch.setattr(daily_briefing, "get_settings", _settings)
    monkeypatch.setattr(daily_briefing, "OllamaClient", InvalidOllama)

    response = client.get("/api/ai/briefing")

    assert response.status_code == 200
    assert response.json()["generation_status"] == "pending"
    assert response.json()["error_message"] == (
        "Ollama returned a briefing that did not pass validation."
    )


def test_briefing_can_include_validated_project_suggestions(
    client: TestClient,
    monkeypatch,
) -> None:
    project = client.post(
        "/api/projects",
        json={"title": "Portfolio refresh", "importance": 4},
    ).json()

    class ProjectSuggestionOllama:
        def __init__(self, *, project_id: str, **_kwargs: Any) -> None:
            self.project_id = project_id

        def generate_json(self, **_kwargs: Any) -> dict[str, Any]:
            return {
                "overview": "Make progress on one meaningful project.",
                "priorities": [],
                "principle_reminders": [],
                "project_recommendations": [
                    {"project_id": self.project_id, "reason": "It is an active project."}
                ],
                "focus_advice": "Choose a small next step.",
            }

    monkeypatch.setattr(daily_briefing, "get_settings", _settings)
    monkeypatch.setattr(
        daily_briefing,
        "OllamaClient",
        lambda **_kwargs: ProjectSuggestionOllama(project_id=project["id"]),
    )
    valid = client.get("/api/ai/briefing")
    assert valid.status_code == 200
    assert valid.json()["generation_status"] == "generated"
    assert valid.json()["content"]["project_recommendations"][0]["project_title"] == (
        "Portfolio refresh"
    )


def test_briefing_rejects_unrecognized_project_suggestions(
    client: TestClient,
    monkeypatch,
) -> None:
    class UnknownProjectOllama:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def generate_json(self, **_kwargs: Any) -> dict[str, Any]:
            return {
                "overview": "Make progress.",
                "priorities": [],
                "principle_reminders": [],
                "project_recommendations": [
                    {"project_id": "not-a-project", "reason": "Not grounded in context."}
                ],
                "focus_advice": "Review your priorities.",
            }

    monkeypatch.setattr(daily_briefing, "get_settings", _settings)
    monkeypatch.setattr(daily_briefing, "OllamaClient", UnknownProjectOllama)

    response = client.get("/api/ai/briefing")

    assert response.status_code == 200
    assert response.json()["generation_status"] == "pending"
    assert response.json()["error_message"] == (
        "Ollama returned a briefing that did not pass validation."
    )
