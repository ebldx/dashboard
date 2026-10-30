from datetime import date
from types import SimpleNamespace

from app.core.ownership import DEFAULT_OWNER_ID
from app import automation


class FakeSession:
    def __init__(self, value: date) -> None:
        self.value = value

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *_args: object) -> None:
        pass

    def scalar(self, _query: object) -> date:
        return self.value


def test_daily_retry_job_processes_due_pending_briefing(
    monkeypatch,
) -> None:
    pending_date = date(2026, 1, 5)
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(automation, "SessionLocal", lambda: FakeSession(pending_date))

    def fake_get_or_create(
        session: object,
        owner_id: str,
        local_date: date,
        *,
        retry_pending: bool,
    ) -> SimpleNamespace:
        calls.append((session, owner_id, local_date, retry_pending))
        return SimpleNamespace(
            local_date=local_date,
            generation_status="pending",
            attempt_count=2,
            next_retry_at=None,
        )

    monkeypatch.setattr(automation, "get_or_create_briefing", fake_get_or_create)

    assert automation.run_retry_daily() == 0
    assert calls[0][1:] == (DEFAULT_OWNER_ID, pending_date, True)


def test_weekly_retry_job_processes_oldest_pending_review(
    monkeypatch,
) -> None:
    pending_week = date(2026, 1, 5)
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(automation, "SessionLocal", lambda: FakeSession(pending_week))

    def fake_get_or_create(
        session: object,
        owner_id: str,
        week_start: date,
        *,
        retry_pending: bool,
    ) -> SimpleNamespace:
        calls.append((session, owner_id, week_start, retry_pending))
        return SimpleNamespace(
            week_start=week_start,
            generation_status="pending",
            attempt_count=2,
            next_retry_at=None,
        )

    monkeypatch.setattr(automation, "get_or_create_weekly_review", fake_get_or_create)

    assert automation.run_retry_weekly() == 0
    assert calls[0][1:] == (DEFAULT_OWNER_ID, pending_week, True)
