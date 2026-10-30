from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.ownership import DEFAULT_OWNER_ID
from app.db.session import get_db
from app.schemas.ai import DailyBriefingRead, OllamaStatus, WeeklyReviewRead
from app.schemas.planning import PlanningSnapshot
from app.services.daily_briefing import get_ollama_status, get_or_create_briefing
from app.services.planning import build_planning_snapshot
from app.services.weekly_review import (
    LOCAL_TIMEZONE,
    get_or_create_weekly_review,
    last_complete_week_start,
    weekly_review_read,
)

router = APIRouter(tags=["ai"])


@router.get("/status", response_model=OllamaStatus)
def ollama_status() -> OllamaStatus:
    return OllamaStatus(**get_ollama_status())


@router.get("/planning", response_model=PlanningSnapshot)
def daily_planning(session: Session = Depends(get_db)) -> PlanningSnapshot:
    return build_planning_snapshot(session, DEFAULT_OWNER_ID)


@router.get("/briefing", response_model=DailyBriefingRead)
def daily_briefing(session: Session = Depends(get_db)) -> DailyBriefingRead:
    return get_or_create_briefing(session, DEFAULT_OWNER_ID)


@router.post("/briefing/retry", response_model=DailyBriefingRead)
def retry_daily_briefing(session: Session = Depends(get_db)) -> DailyBriefingRead:
    return get_or_create_briefing(
        session,
        DEFAULT_OWNER_ID,
        retry_pending=True,
        force_retry=True,
    )


def _week_start(value: date | None) -> date:
    selected = value or last_complete_week_start()
    if selected.weekday() != 0:
        raise HTTPException(status_code=422, detail="week_start must be a Monday.")
    if selected > last_complete_week_start(
        datetime.now(LOCAL_TIMEZONE).date()
    ):
        raise HTTPException(status_code=422, detail="week_start must refer to a completed week.")
    return selected


@router.get("/weekly-review", response_model=WeeklyReviewRead)
def weekly_review(
    week_start: date | None = Query(default=None),
    session: Session = Depends(get_db),
) -> WeeklyReviewRead:
    selected_week = _week_start(week_start)
    review = get_or_create_weekly_review(session, DEFAULT_OWNER_ID, selected_week)
    return WeeklyReviewRead(**weekly_review_read(review))


@router.post("/weekly-review/retry", response_model=WeeklyReviewRead)
def retry_weekly_review(
    week_start: date | None = Query(default=None),
    session: Session = Depends(get_db),
) -> WeeklyReviewRead:
    selected_week = _week_start(week_start)
    review = get_or_create_weekly_review(
        session,
        DEFAULT_OWNER_ID,
        selected_week,
        retry_pending=True,
        force_retry=True,
    )
    return WeeklyReviewRead(**weekly_review_read(review))
