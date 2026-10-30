from datetime import date

from fastapi.testclient import TestClient


def _feedback_payload(local_date: str, **overrides: object) -> dict:
    return {
        "local_date": local_date,
        "rating": 1,
        "comment": "The suggested pacing felt useful.",
        "preference_field": "planning_preferences",
        "candidate_value": "Keep the daily plan to three priorities.",
        "explicitly_requested": False,
        **overrides,
    }


def test_feedback_creates_reviewable_candidate_then_accept_and_undo(
    client: TestClient,
) -> None:
    briefing = client.get("/api/ai/briefing").json()
    local_date = briefing["local_date"]

    feedback = client.post(
        "/api/preferences/feedback",
        json=_feedback_payload(local_date),
    )
    assert feedback.status_code == 200
    assert feedback.json()["rating"] == 1
    assert feedback.json()["local_date"] == local_date

    workspace = client.get("/api/preferences/learning").json()
    candidate = workspace["candidates"][0]
    assert candidate["status"] == "pending"
    assert candidate["current_value"] == ""
    assert workspace["current_preferences"]["planning_preferences"] == ""
    assert workspace["feedback"][0]["comment"] == "The suggested pacing felt useful."

    accepted = client.post(
        f"/api/preferences/candidates/{candidate['id']}/accept",
        json={},
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "applied"
    assert client.get("/api/profile").json()["planning_preferences"] == (
        "Keep the daily plan to three priorities."
    )

    history = client.get("/api/preferences/learning").json()["history"][0]
    undone = client.post(
        f"/api/preferences/history/{history['id']}/undo",
        json={},
    )
    assert undone.status_code == 200
    assert undone.json()["previous_value"] == ""
    assert undone.json()["undone_at"] is not None
    assert client.get("/api/profile").json()["planning_preferences"] == ""
    assert client.get("/api/preferences/learning").json()["candidates"][0]["status"] == "undone"


def test_feedback_updates_the_existing_daily_record_and_pending_candidate(
    client: TestClient,
) -> None:
    briefing = client.get("/api/ai/briefing").json()
    local_date = briefing["local_date"]
    first = client.post(
        "/api/preferences/feedback",
        json=_feedback_payload(local_date),
    )
    second = client.post(
        "/api/preferences/feedback",
        json=_feedback_payload(
            local_date,
            rating=-1,
            comment="Please make it more concise.",
            candidate_value="Keep the briefing to a short summary.",
        ),
    )

    assert first.status_code == second.status_code == 200
    workspace = client.get("/api/preferences/learning").json()
    assert len(workspace["feedback"]) == 1
    assert workspace["feedback"][0]["id"] == first.json()["id"]
    assert workspace["feedback"][0]["rating"] == -1
    assert workspace["feedback"][0]["comment"] == "Please make it more concise."
    assert len(workspace["candidates"]) == 1
    assert workspace["candidates"][0]["candidate_value"] == (
        "Keep the briefing to a short summary."
    )


def test_explicit_opt_in_is_the_only_auto_apply_rule(client: TestClient) -> None:
    briefing = client.get("/api/ai/briefing").json()
    local_date = briefing["local_date"]

    saved_feedback = client.post(
        "/api/preferences/feedback",
        json=_feedback_payload(
            local_date,
            rating=-1,
            explicitly_requested=True,
        ),
    )
    assert saved_feedback.status_code == 200
    workspace = client.get("/api/preferences/learning").json()
    candidate = workspace["candidates"][0]
    assert candidate["status"] == "applied"
    assert candidate["auto_applied"] is True
    assert workspace["history"][0]["applied_value"] == (
        "Keep the daily plan to three priorities."
    )
    assert client.get("/api/profile").json()["planning_preferences"] == (
        "Keep the daily plan to three priorities."
    )


def test_preference_candidates_can_be_edited_and_rejected(client: TestClient) -> None:
    briefing = client.get("/api/ai/briefing").json()
    feedback = client.post(
        "/api/preferences/feedback",
        json=_feedback_payload(briefing["local_date"]),
    )
    assert feedback.status_code == 200
    candidate = client.get("/api/preferences/learning").json()["candidates"][0]

    edited = client.patch(
        f"/api/preferences/candidates/{candidate['id']}",
        json={"candidate_value": "Use a shorter, more focused daily plan."},
    )
    assert edited.status_code == 200
    assert edited.json()["candidate_value"] == "Use a shorter, more focused daily plan."
    rejected = client.post(
        f"/api/preferences/candidates/{candidate['id']}/reject",
        json={},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert client.get("/api/profile").json()["planning_preferences"] == ""


def test_undo_refuses_to_overwrite_a_newer_preference_change(client: TestClient) -> None:
    briefing = client.get("/api/ai/briefing").json()
    first = client.post(
        "/api/preferences/feedback",
        json=_feedback_payload(
            briefing["local_date"],
            candidate_value="Prefer concise plans.",
            explicitly_requested=True,
        ),
    )
    assert first.status_code == 200
    history_id = client.get("/api/preferences/learning").json()["history"][0]["id"]

    updated = client.patch(
        "/api/profile",
        json={"planning_preferences": "I changed this directly in my profile."},
    )
    assert updated.status_code == 200
    response = client.post(
        f"/api/preferences/history/{history_id}/undo",
        json={},
    )
    assert response.status_code == 409
    assert client.get("/api/profile").json()["planning_preferences"] == (
        "I changed this directly in my profile."
    )


def test_direct_profile_preference_changes_are_reversible(client: TestClient) -> None:
    updated = client.patch(
        "/api/profile",
        json={"focus_preferences": "I prefer single-task focus blocks."},
    )
    assert updated.status_code == 200
    workspace = client.get("/api/preferences/learning").json()
    history = workspace["history"][0]
    assert history["source"] == "profile_edit"
    assert history["candidate_id"] is None

    undone = client.post(
        f"/api/preferences/history/{history['id']}/undo",
        json={},
    )

    assert undone.status_code == 200
    assert client.get("/api/profile").json()["focus_preferences"] == ""


def test_feedback_validation_requires_complete_and_explicit_candidate(
    client: TestClient,
) -> None:
    today = date.today().isoformat()
    missing_value = client.post(
        "/api/preferences/feedback",
        json={
            "local_date": today,
            "rating": 0,
            "preference_field": "focus_preferences",
        },
    )
    assert missing_value.status_code == 422

    missing_candidate = client.post(
        "/api/preferences/feedback",
        json={
            "local_date": today,
            "rating": 0,
            "explicitly_requested": True,
        },
    )
    assert missing_candidate.status_code == 422

    invalid_field = client.post(
        "/api/preferences/feedback",
        json={
            "local_date": today,
            "rating": 0,
            "preference_field": "background",
            "candidate_value": "Do not replace profile background.",
        },
    )
    assert invalid_field.status_code == 422
