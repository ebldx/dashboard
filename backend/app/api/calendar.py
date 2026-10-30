from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.ownership import DEFAULT_OWNER_ID
from app.db.models import CalendarEvent, CalendarSource
from app.db.session import get_db
from app.schemas.calendar import (
    CalendarEventRead,
    CalendarSourceStatus,
    CalendarSourceUpdate,
    CalendarSyncResult,
)
from app.services.calendar_sync import (
    CalendarEncryptionError,
    CalendarSyncError,
    SOURCE_ADAPTER,
    clear_calendar_events,
    decrypt_calendar_url,
    encrypt_calendar_url,
    sync_calendar_source,
)

router = APIRouter(tags=["calendar"])
DISPLAY_TIMEZONE = ZoneInfo("Europe/Oslo")


def _source(session: Session) -> CalendarSource | None:
    return session.scalar(
        select(CalendarSource).where(
            CalendarSource.owner_id == DEFAULT_OWNER_ID,
            CalendarSource.adapter == SOURCE_ADAPTER,
        )
    )


def _status(source: CalendarSource | None) -> CalendarSourceStatus:
    def utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    return CalendarSourceStatus(
        configured=source is not None and source.enabled,
        enabled=source.enabled if source else False,
        adapter=source.adapter if source else None,
        display_name=source.display_name if source else None,
        sync_status=source.sync_status if source else "not_configured",
        last_sync_attempt_at=utc(source.last_sync_attempt_at) if source else None,
        last_successful_sync_at=utc(source.last_successful_sync_at) if source else None,
        last_sync_error=source.last_sync_error if source else None,
        last_event_count=source.last_event_count if source else 0,
        last_created_count=source.last_created_count if source else 0,
        last_updated_count=source.last_updated_count if source else 0,
        last_deleted_count=source.last_deleted_count if source else 0,
    )


def _event_read(event: CalendarEvent) -> CalendarEventRead:
    starts_at = event.starts_at
    ends_at = event.ends_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=UTC)
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=UTC)
    return CalendarEventRead(
        id=event.id,
        source_id=event.source_id,
        source_name=event.source.display_name,
        source_uid=event.source_uid,
        title=event.title,
        description=event.description,
        location=event.location,
        starts_at=starts_at,
        ends_at=ends_at,
        local_date=starts_at.astimezone(DISPLAY_TIMEZONE).date(),
        all_day=event.all_day,
        source_timezone=event.source_timezone,
        status=event.status,
    )


@router.get("/status", response_model=CalendarSourceStatus)
def get_calendar_status(session: Session = Depends(get_db)) -> CalendarSourceStatus:
    return _status(_source(session))


@router.patch("/source", response_model=CalendarSourceStatus)
def update_calendar_source(
    changes: CalendarSourceUpdate,
    session: Session = Depends(get_db),
) -> CalendarSourceStatus:
    source = _source(session)
    feed_url = changes.feed_url.strip()
    if not feed_url:
        if source is not None:
            session.delete(source)
            session.commit()
        return _status(None)

    try:
        if source is not None and decrypt_calendar_url(source.feed_url_encrypted) == feed_url:
            return _status(source)
        encrypted_feed_url = encrypt_calendar_url(feed_url)
    except CalendarEncryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if source is None:
        source = CalendarSource(
            owner_id=DEFAULT_OWNER_ID,
            adapter=SOURCE_ADAPTER,
            display_name="Mine studier",
            feed_url_encrypted=encrypted_feed_url,
            enabled=True,
        )
        session.add(source)
    else:
        clear_calendar_events(session, source.id)
        source.feed_url_encrypted = encrypted_feed_url
        source.etag = None
        source.last_modified = None
        source.sync_status = "never_synced"
        source.last_sync_attempt_at = None
        source.last_successful_sync_at = None
        source.last_sync_error = None
        source.last_event_count = 0
        source.last_created_count = 0
        source.last_updated_count = 0
        source.last_deleted_count = 0
    source.enabled = True
    session.commit()
    return _status(source)


@router.post("/sync", response_model=CalendarSyncResult)
def sync_calendar(session: Session = Depends(get_db)) -> CalendarSyncResult:
    source = _source(session)
    if source is None or not source.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Configure a calendar subscription before synchronizing.",
        )
    try:
        result = sync_calendar_source(session, source)
    except CalendarSyncError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return CalendarSyncResult(**result)


@router.get("/events", response_model=list[CalendarEventRead])
def list_calendar_events(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    session: Session = Depends(get_db),
) -> list[CalendarEventRead]:
    today = datetime.now(DISPLAY_TIMEZONE).date()
    start_date = from_date or today
    end_date = to_date or start_date + timedelta(days=6)
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="to_date cannot be before from_date")
    if (end_date - start_date).days > 30:
        raise HTTPException(status_code=422, detail="Calendar ranges cannot exceed 31 days")

    start_at = datetime.combine(start_date, time.min, tzinfo=DISPLAY_TIMEZONE)
    end_at = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=DISPLAY_TIMEZONE)
    events = session.scalars(
        select(CalendarEvent)
        .options(joinedload(CalendarEvent.source))
        .where(
            CalendarEvent.owner_id == DEFAULT_OWNER_ID,
            CalendarEvent.starts_at < end_at.astimezone(UTC),
            CalendarEvent.ends_at > start_at.astimezone(UTC),
        )
        .order_by(CalendarEvent.starts_at, CalendarEvent.title)
    ).unique()
    return [_event_read(event) for event in events]
