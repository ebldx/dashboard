import ipaddress
import socket
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx
import recurring_ical_events
from cryptography.fernet import Fernet, InvalidToken
from icalendar import Calendar
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.ownership import DEFAULT_OWNER_ID
from app.core.config import get_settings
from app.db.models import CalendarEvent, CalendarSource

DISPLAY_TIMEZONE = ZoneInfo("Europe/Oslo")
SYNC_PAST_DAYS = 90
SYNC_FUTURE_DAYS = 365
MAX_FEED_BYTES = 5 * 1024 * 1024
MAX_EVENT_OCCURRENCES = 20_000
SOURCE_ADAPTER = "icalendar"


class CalendarSyncError(Exception):
    pass


class CalendarEncryptionError(Exception):
    pass


@dataclass(frozen=True)
class DownloadedFeed:
    content: bytes | None
    etag: str | None
    last_modified: str | None
    not_modified: bool = False


@dataclass(frozen=True)
class EventData:
    source_uid: str
    occurrence_key: str
    title: str
    description: str
    location: str
    starts_at: datetime
    ends_at: datetime
    all_day: bool
    source_timezone: str
    status: str
    source_updated_at: datetime | None


@dataclass(frozen=True)
class CalendarSnapshot:
    events: list[EventData] | None
    etag: str | None
    last_modified: str | None
    not_modified: bool = False


class CalendarAdapter(Protocol):
    def fetch(
        self,
        source: CalendarSource,
        window_start: datetime,
        window_end: datetime,
    ) -> CalendarSnapshot: ...


def _validate_public_https_destination(feed_url: str) -> None:
    parsed = urlsplit(feed_url)
    hostname = parsed.hostname
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise CalendarSyncError(
            "The calendar subscription must be an HTTPS URL without embedded credentials."
        )
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise CalendarSyncError("The calendar subscription host is not allowed.")

    if hostname.lower().rstrip(".") in {"localhost", "localhost.localdomain"}:
        raise CalendarSyncError("The calendar subscription host is not allowed.")
    try:
        addresses = socket.getaddrinfo(
            hostname,
            parsed.port or 443,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise CalendarSyncError("The calendar subscription host could not be resolved.") from exc
    resolved = {ipaddress.ip_address(item[4][0]) for item in addresses}
    if not resolved or any(not address.is_global for address in resolved):
        raise CalendarSyncError("The calendar subscription host is not publicly routable.")


def _fernet() -> Fernet:
    key_setting = get_settings().calendar_encryption_key
    if key_setting is None or not key_setting.get_secret_value().strip():
        raise CalendarEncryptionError(
            "Set CALENDAR_ENCRYPTION_KEY before configuring a calendar subscription."
        )
    try:
        return Fernet(key_setting.get_secret_value().encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise CalendarEncryptionError(
            "CALENDAR_ENCRYPTION_KEY is invalid; generate a Fernet key and restart the API."
        ) from exc


def encrypt_calendar_url(feed_url: str) -> str:
    return _fernet().encrypt(feed_url.encode("utf-8")).decode("ascii")


def decrypt_calendar_url(encrypted_url: str) -> str:
    try:
        return _fernet().decrypt(encrypted_url.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise CalendarEncryptionError(
            "The saved calendar subscription cannot be decrypted; check CALENDAR_ENCRYPTION_KEY."
        ) from exc


def _download_feed(source: CalendarSource) -> DownloadedFeed:
    try:
        feed_url = decrypt_calendar_url(source.feed_url_encrypted)
    except CalendarEncryptionError as exc:
        raise CalendarSyncError(str(exc)) from exc
    _validate_public_https_destination(feed_url)
    headers = {"Accept": "text/calendar, text/plain;q=0.9"}
    if source.etag:
        headers["If-None-Match"] = source.etag
    if source.last_modified:
        headers["If-Modified-Since"] = source.last_modified

    try:
        with httpx.Client(
            timeout=httpx.Timeout(20.0, connect=8.0),
            follow_redirects=False,
            trust_env=False,
        ) as client:
            with client.stream("GET", feed_url, headers=headers) as response:
                if response.status_code == 304:
                    return DownloadedFeed(
                        content=None,
                        etag=source.etag,
                        last_modified=source.last_modified,
                        not_modified=True,
                    )
                if response.is_redirect:
                    raise CalendarSyncError("Calendar subscriptions may not redirect.")
                if response.status_code != 200:
                    raise CalendarSyncError(
                        f"The calendar provider returned HTTP {response.status_code}."
                    )
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_FEED_BYTES:
                    raise CalendarSyncError("The calendar feed is larger than 5 MB.")
                chunks: list[bytes] = []
                total_bytes = 0
                for chunk in response.iter_bytes():
                    total_bytes += len(chunk)
                    if total_bytes > MAX_FEED_BYTES:
                        raise CalendarSyncError("The calendar feed is larger than 5 MB.")
                    chunks.append(chunk)
                return DownloadedFeed(
                    content=b"".join(chunks),
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                )
    except CalendarSyncError:
        raise
    except httpx.HTTPError as exc:
        raise CalendarSyncError("Could not retrieve the calendar feed.") from exc
    except ValueError as exc:
        raise CalendarSyncError("The calendar provider returned an invalid response.") from exc


def _datetime_value(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=DISPLAY_TIMEZONE)
        return value
    return datetime.combine(value, time.min, tzinfo=DISPLAY_TIMEZONE)


def _event_timezone(component) -> str:
    start = component.get("DTSTART")
    if start is None:
        return "Europe/Oslo"
    tzid = start.params.get("TZID")
    if tzid:
        return str(tzid)
    value = start.dt
    if isinstance(value, datetime) and value.tzinfo is not None:
        return getattr(value.tzinfo, "key", None) or "UTC"
    return "Europe/Oslo"


def _identity_datetime(value: date | datetime) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return value.isoformat()


def _parse_feed(content: bytes, window_start: datetime, window_end: datetime) -> list[EventData]:
    try:
        calendar = Calendar.from_ical(content)
    except Exception as exc:
        raise CalendarSyncError("The subscription did not contain a valid iCalendar feed.") from exc
    if calendar.name != "VCALENDAR":
        raise CalendarSyncError("The subscription did not contain a valid iCalendar feed.")

    for component in calendar.walk("VEVENT"):
        uid = component.get("UID")
        if uid is None or not str(uid).strip():
            raise CalendarSyncError("Every calendar event must have a source UID.")
        rule = component.get("RRULE")
        if rule is not None:
            frequency = str(rule.get("FREQ", [""])[0]).upper()
            if frequency in {"SECONDLY", "MINUTELY"}:
                raise CalendarSyncError(
                    "Calendar recurrences more frequent than hourly are not supported."
                )

    try:
        occurrences = recurring_ical_events.of(calendar).between(window_start, window_end)
    except Exception as exc:
        raise CalendarSyncError("The calendar feed contains an unsupported recurrence rule.") from exc
    if len(occurrences) > MAX_EVENT_OCCURRENCES:
        raise CalendarSyncError("The calendar feed expands to too many event occurrences.")

    events: list[EventData] = []
    seen: set[tuple[str, str]] = set()
    for component in occurrences:
        try:
            uid = str(component.get("UID")).strip()
            start_value = component.decoded("DTSTART")
            end_property = component.get("DTEND")
            if end_property is not None:
                end_value = end_property.dt
            elif component.get("DURATION") is not None:
                end_value = start_value + component.decoded("DURATION")
            else:
                end_value = start_value
            timezone_name = _event_timezone(component)
            starts_at = _datetime_value(start_value)
            ends_at = _datetime_value(end_value)
            if ends_at < starts_at:
                raise ValueError("Event end precedes start")
            recurrence_id = component.get("RECURRENCE-ID")
            occurrence_key = (
                _identity_datetime(recurrence_id.dt)
                if recurrence_id is not None
                else "single"
            )
            identity = (uid, occurrence_key)
            if identity in seen:
                continue
            seen.add(identity)
            updated_value = component.get("LAST-MODIFIED")
            status_value = str(component.get("STATUS", "CONFIRMED")).upper()
            events.append(
                EventData(
                    source_uid=uid,
                    occurrence_key=occurrence_key,
                    title=str(component.get("SUMMARY", "(No title)"))[:500],
                    description=str(component.get("DESCRIPTION", "")),
                    location=str(component.get("LOCATION", ""))[:1000],
                    starts_at=starts_at.astimezone(UTC),
                    ends_at=ends_at.astimezone(UTC),
                    all_day=not isinstance(start_value, datetime),
                    source_timezone=timezone_name[:100],
                    status="cancelled" if status_value == "CANCELLED" else (
                        "tentative" if status_value == "TENTATIVE" else "confirmed"
                    ),
                    source_updated_at=(
                        _datetime_value(updated_value).astimezone(UTC)
                        if updated_value is not None
                        else None
                    ),
                )
            )
        except CalendarSyncError:
            raise
        except Exception as exc:
            raise CalendarSyncError("The calendar feed contains an invalid event.") from exc
    return events


class IcalendarSubscriptionAdapter:
    def fetch(
        self,
        source: CalendarSource,
        window_start: datetime,
        window_end: datetime,
    ) -> CalendarSnapshot:
        downloaded = _download_feed(source)
        if downloaded.not_modified:
            return CalendarSnapshot(
                events=None,
                etag=downloaded.etag,
                last_modified=downloaded.last_modified,
                not_modified=True,
            )
        if downloaded.content is None:
            raise CalendarSyncError("The calendar provider returned an empty feed.")
        return CalendarSnapshot(
            events=_parse_feed(downloaded.content, window_start, window_end),
            etag=downloaded.etag,
            last_modified=downloaded.last_modified,
        )


CALENDAR_ADAPTERS: dict[str, CalendarAdapter] = {
    SOURCE_ADAPTER: IcalendarSubscriptionAdapter(),
}


def sync_calendar_source(session: Session, source: CalendarSource) -> dict[str, int | datetime]:
    now = datetime.now(UTC)
    source.last_sync_attempt_at = now
    try:
        local_today = now.astimezone(DISPLAY_TIMEZONE).date()
        lower = datetime.combine(
            local_today - timedelta(days=SYNC_PAST_DAYS),
            time.min,
            tzinfo=DISPLAY_TIMEZONE,
        )
        upper = datetime.combine(
            local_today + timedelta(days=SYNC_FUTURE_DAYS),
            time.min,
            tzinfo=DISPLAY_TIMEZONE,
        )
        adapter = CALENDAR_ADAPTERS.get(source.adapter)
        if adapter is None:
            raise CalendarSyncError("The configured calendar adapter is not supported.")
        snapshot = adapter.fetch(source, lower, upper)
        if snapshot.not_modified:
            source.sync_status = "success"
            source.last_sync_error = None
            source.last_created_count = 0
            source.last_updated_count = 0
            source.last_deleted_count = 0
            source.last_successful_sync_at = now
            session.commit()
            return {
                "status": "not_modified",
                "created": 0,
                "updated": 0,
                "deleted": 0,
                "event_count": source.last_event_count,
                "last_successful_sync_at": now,
            }

        if snapshot.events is None:
            raise CalendarSyncError("The calendar adapter returned no event data.")
        event_data = snapshot.events
        existing = {
            (event.source_uid, event.occurrence_key): event
            for event in session.scalars(
                select(CalendarEvent).where(
                    CalendarEvent.source_id == source.id,
                    CalendarEvent.owner_id == DEFAULT_OWNER_ID,
                )
            )
        }
        created_count = 0
        updated_count = 0
        identities: set[tuple[str, str]] = set()
        for item in event_data:
            identity = (item.source_uid, item.occurrence_key)
            identities.add(identity)
            current = existing.get(identity)
            values = {
                "title": item.title,
                "description": item.description,
                "location": item.location,
                "starts_at": item.starts_at,
                "ends_at": item.ends_at,
                "all_day": item.all_day,
                "source_timezone": item.source_timezone,
                "status": item.status,
                "source_updated_at": item.source_updated_at,
            }
            if current is None:
                session.add(
                    CalendarEvent(
                        owner_id=DEFAULT_OWNER_ID,
                        source_id=source.id,
                        source_uid=item.source_uid,
                        occurrence_key=item.occurrence_key,
                        **values,
                    )
                )
                created_count += 1
                continue
            if any(
                not _values_match(getattr(current, key), value)
                for key, value in values.items()
            ):
                for key, value in values.items():
                    setattr(current, key, value)
                updated_count += 1

        lower_utc = lower.astimezone(UTC).replace(tzinfo=None)
        upper_utc = upper.astimezone(UTC).replace(tzinfo=None)
        existing_in_window = list(
            session.scalars(
                select(CalendarEvent).where(
                    CalendarEvent.source_id == source.id,
                    CalendarEvent.owner_id == DEFAULT_OWNER_ID,
                    CalendarEvent.starts_at >= lower_utc,
                    CalendarEvent.starts_at < upper_utc,
                )
            )
        )
        deleted_count = 0
        for old_event in existing_in_window:
            if (old_event.source_uid, old_event.occurrence_key) not in identities:
                session.delete(old_event)
                deleted_count += 1

        session.flush()
        source.etag = snapshot.etag
        source.last_modified = snapshot.last_modified
        source.sync_status = "success"
        source.last_sync_error = None
        source.last_event_count = len(event_data)
        source.last_created_count = created_count
        source.last_updated_count = updated_count
        source.last_deleted_count = deleted_count
        source.last_successful_sync_at = now
        session.commit()
        return {
            "status": "success",
            "created": created_count,
            "updated": updated_count,
            "deleted": deleted_count,
            "event_count": len(event_data),
            "last_successful_sync_at": now,
        }
    except CalendarSyncError as exc:
        session.rollback()
        source = session.get(CalendarSource, source.id)
        if source is not None:
            source.last_sync_attempt_at = now
            source.sync_status = "error"
            source.last_sync_error = str(exc)
            session.commit()
        raise
    except Exception as exc:
        session.rollback()
        source = session.get(CalendarSource, source.id)
        if source is not None:
            source.last_sync_attempt_at = now
            source.sync_status = "error"
            source.last_sync_error = "Calendar synchronization failed."
            session.commit()
        raise CalendarSyncError("Calendar synchronization failed.") from exc


def clear_calendar_events(session: Session, source_id: str) -> int:
    result = session.execute(
        delete(CalendarEvent).where(
            CalendarEvent.source_id == source_id,
            CalendarEvent.owner_id == DEFAULT_OWNER_ID,
        )
    )
    return result.rowcount or 0


def _values_match(current, new_value) -> bool:
    if isinstance(current, datetime) and isinstance(new_value, datetime):
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        if new_value.tzinfo is None:
            new_value = new_value.replace(tzinfo=UTC)
    return current == new_value
