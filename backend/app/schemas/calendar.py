from datetime import date, datetime
from urllib.parse import urlsplit

from pydantic import Field, field_validator

from app.schemas.personal import APIModel


class CalendarSourceUpdate(APIModel):
    feed_url: str = Field(max_length=8192)

    @field_validator("feed_url")
    @classmethod
    def validate_feed_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            return normalized
        parsed = urlsplit(normalized)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ValueError(
                "Calendar subscriptions must be HTTPS URLs without embedded credentials or fragments"
            )
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("The calendar subscription URL contains an invalid port") from exc
        return normalized


class CalendarSourceStatus(APIModel):
    configured: bool
    enabled: bool
    adapter: str | None
    display_name: str | None
    sync_status: str
    last_sync_attempt_at: datetime | None
    last_successful_sync_at: datetime | None
    last_sync_error: str | None
    last_event_count: int
    last_created_count: int
    last_updated_count: int
    last_deleted_count: int


class CalendarEventRead(APIModel):
    id: str
    source_id: str
    source_name: str
    source_uid: str
    title: str
    description: str
    location: str
    starts_at: datetime
    ends_at: datetime
    local_date: date
    all_day: bool
    source_timezone: str
    status: str


class CalendarSyncResult(APIModel):
    status: str
    created: int
    updated: int
    deleted: int
    event_count: int
    last_successful_sync_at: datetime
