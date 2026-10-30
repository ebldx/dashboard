from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from icalendar import Calendar, Event

from app.services import calendar_sync
from app.services.calendar_sync import CalendarSyncError, DownloadedFeed

OSLO = ZoneInfo("Europe/Oslo")


def _feed(
    *,
    recurring_summary: str = "Programming lecture",
    include_all_day: bool = True,
) -> bytes:
    calendar = Calendar()
    calendar.add("prodid", "-//Daymark calendar test//EN")
    calendar.add("version", "2.0")
    start = datetime.now(OSLO).replace(hour=10, minute=0, second=0, microsecond=0)
    start += timedelta(days=2)

    recurring = Event()
    recurring.add("uid", "class-series-42")
    recurring.add("dtstart", start)
    recurring.add("dtend", start + timedelta(hours=1))
    recurring.add("rrule", {"freq": "daily", "count": 3})
    recurring.add("summary", recurring_summary)
    recurring.add("location", "Room 204")
    calendar.add_component(recurring)

    cancelled = Event()
    cancelled.add("uid", "cancelled-lesson")
    cancelled.add("dtstart", start + timedelta(days=4))
    cancelled.add("dtend", start + timedelta(days=4, hours=1))
    cancelled.add("summary", "Cancelled lecture")
    cancelled.add("status", "CANCELLED")
    calendar.add_component(cancelled)

    if include_all_day:
        all_day = Event()
        all_day.add("uid", "exam-day")
        all_day.add("dtstart", (start + timedelta(days=1)).date())
        all_day.add("dtend", (start + timedelta(days=2)).date())
        all_day.add("summary", "Exam day")
        calendar.add_component(all_day)

    return calendar.to_ical()


def _configure(client: TestClient) -> dict:
    response = client.patch(
        "/api/calendar/source",
        json={"feed_url": "https://calendar.example.test/secret-subscription-token"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["configured"] is True
    assert "feed_url" not in result
    assert "secret-subscription-token" not in response.text
    return result


def test_calendar_source_requires_https_and_never_returns_subscription_url(
    client: TestClient,
) -> None:
    assert client.get("/api/calendar/status").json()["configured"] is False
    invalid = client.patch(
        "/api/calendar/source",
        json={"feed_url": "http://calendar.example.test/private.ics"},
    )
    assert invalid.status_code == 422
    embedded_credentials = client.patch(
        "/api/calendar/source",
        json={"feed_url": "https://user:password@calendar.example.test/feed.ics"},
    )
    assert embedded_credentials.status_code == 422

    configured = _configure(client)
    assert configured["display_name"] == "Mine studier"
    assert client.get("/api/calendar/status").json()["configured"] is True


def test_calendar_sync_deduplicates_recurring_events_and_records_changes(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(client)
    current_feed = _feed()
    monkeypatch.setattr(
        calendar_sync,
        "_download_feed",
        lambda _source: DownloadedFeed(current_feed, '"test-etag"', None),
    )

    first_sync = client.post("/api/calendar/sync")
    assert first_sync.status_code == 200
    assert first_sync.json()["created"] == 5
    events = client.get("/api/calendar/events").json()
    assert len(events) == 5
    series = [event for event in events if event["source_uid"] == "class-series-42"]
    assert len(series) == 3
    assert {event["source_name"] for event in events} == {"Mine studier"}
    assert {event["source_timezone"] for event in series} == {"Europe/Oslo"}
    assert all(event["starts_at"].endswith("Z") for event in events)
    assert next(event for event in events if event["source_uid"] == "exam-day")["all_day"]
    assert next(
        event for event in events if event["source_uid"] == "cancelled-lesson"
    )["status"] == "cancelled"

    unchanged = client.post("/api/calendar/sync").json()
    assert unchanged["created"] == 0
    assert unchanged["updated"] == 0
    assert unchanged["deleted"] == 0

    current_feed = _feed(recurring_summary="Updated lecture", include_all_day=False)
    changed = client.post("/api/calendar/sync").json()
    assert changed["created"] == 0
    assert changed["updated"] == 3
    assert changed["deleted"] == 1
    events_after_update = client.get("/api/calendar/events").json()
    assert not any(event["source_uid"] == "exam-day" for event in events_after_update)
    assert all(
        event["title"] == "Updated lecture"
        for event in events_after_update
        if event["source_uid"] == "class-series-42"
    )
    status = client.get("/api/calendar/status").json()
    assert status["sync_status"] == "success"
    assert status["last_updated_count"] == 3
    assert status["last_deleted_count"] == 1


def test_calendar_sync_failure_is_reported_without_losing_existing_events(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(client)
    monkeypatch.setattr(
        calendar_sync,
        "_download_feed",
        lambda _source: DownloadedFeed(_feed(), None, None),
    )
    assert client.post("/api/calendar/sync").status_code == 200
    before = client.get("/api/calendar/events").json()

    monkeypatch.setattr(
        calendar_sync,
        "_download_feed",
        lambda _source: DownloadedFeed(b"not an icalendar feed", None, None),
    )
    failed = client.post("/api/calendar/sync")
    assert failed.status_code == 502
    assert "secret-subscription-token" not in failed.text
    status = client.get("/api/calendar/status").json()
    assert status["sync_status"] == "error"
    assert status["last_sync_error"] == (
        "The subscription did not contain a valid iCalendar feed."
    )
    assert client.get("/api/calendar/events").json() == before


def test_calendar_events_filter_by_local_date_and_source(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(client)
    current_feed = _feed()
    monkeypatch.setattr(
        calendar_sync,
        "_download_feed",
        lambda _source: DownloadedFeed(current_feed, None, None),
    )
    assert client.post("/api/calendar/sync").status_code == 200
    events = client.get(
        "/api/calendar/events",
        params={"from_date": datetime.now(OSLO).date().isoformat(),
                "to_date": (datetime.now(OSLO).date() + timedelta(days=3)).isoformat()},
    ).json()
    assert len(events) == 3
    invalid_range = client.get(
        "/api/calendar/events",
        params={"from_date": "2026-11-01", "to_date": "2026-12-10"},
    )
    assert invalid_range.status_code == 422


def test_recurring_events_keep_local_wall_time_across_daylight_saving() -> None:
    calendar = Calendar()
    calendar.add("prodid", "-//Daymark calendar test//EN")
    calendar.add("version", "2.0")
    event = Event()
    event.add("uid", "dst-series")
    event.add("dtstart", datetime(2027, 3, 26, 10, tzinfo=OSLO))
    event.add("dtend", datetime(2027, 3, 26, 11, tzinfo=OSLO))
    event.add("rrule", {"freq": "daily", "count": 4})
    event.add("summary", "Daylight saving test")
    calendar.add_component(event)
    cancelled = Event()
    cancelled.add("uid", "dst-series")
    cancelled.add("recurrence-id", datetime(2027, 3, 27, 10, tzinfo=OSLO))
    cancelled.add("dtstart", datetime(2027, 3, 27, 10, tzinfo=OSLO))
    cancelled.add("dtend", datetime(2027, 3, 27, 11, tzinfo=OSLO))
    cancelled.add("summary", "Cancelled session")
    cancelled.add("status", "CANCELLED")
    calendar.add_component(cancelled)

    events = calendar_sync._parse_feed(
        calendar.to_ical(),
        datetime(2027, 3, 25, tzinfo=OSLO),
        datetime(2027, 3, 31, tzinfo=OSLO),
    )
    local_starts = [item.starts_at.astimezone(OSLO) for item in events]
    assert [item.hour for item in local_starts] == [10, 10, 10, 10]
    assert local_starts[1].utcoffset() != local_starts[2].utcoffset()
    assert events[1].status == "cancelled"
    assert events[1].title == "Cancelled session"


def test_calendar_configuration_requires_an_encryption_key(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "calendar_encryption_key", None)
    response = client.patch(
        "/api/calendar/source",
        json={"feed_url": "https://calendar.example.test/private.ics"},
    )
    assert response.status_code == 503
    assert "CALENDAR_ENCRYPTION_KEY" in response.json()["detail"]


def test_calendar_sync_rejects_private_feed_destinations() -> None:
    class Source:
        feed_url = "https://127.0.0.1/private.ics"

    with pytest.raises(CalendarSyncError, match="host is not allowed"):
        calendar_sync._validate_public_https_destination(Source.feed_url)


def test_calendar_subscription_secret_is_encrypted_and_conditional_fetch_is_supported(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed_url = "https://calendar.example.test/private-token.ics"
    encrypted = calendar_sync.encrypt_calendar_url(feed_url)
    assert feed_url not in encrypted
    assert calendar_sync.decrypt_calendar_url(encrypted) == feed_url
    monkeypatch.setattr(calendar_sync, "_validate_public_https_destination", lambda _url: None)

    class MockResponse:
        status_code = 304
        headers = {}
        is_redirect = False

    class MockClient:
        def __init__(self, **options) -> None:
            assert options["follow_redirects"] is False
            assert options["trust_env"] is False

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def stream(self, method, url, headers):
            assert method == "GET"
            assert url == feed_url
            assert headers["If-None-Match"] == '"etag-value"'
            return MockResponseContext()

    class MockResponseContext(MockResponse):
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

    monkeypatch.setattr(calendar_sync.httpx, "Client", MockClient)
    source = SimpleNamespace(
        feed_url_encrypted=encrypted,
        etag='"etag-value"',
        last_modified=None,
    )
    downloaded = calendar_sync._download_feed(source)
    assert downloaded.not_modified is True
    assert downloaded.content is None
