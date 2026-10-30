from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.ollama import OllamaError
from app.core.config import get_settings
from app.db.models import (
    CalendarEvent,
    DailyBriefing,
    PreferenceFeedback,
    Task,
    WeeklyReview,
)
from app.schemas.ai import WeeklyReviewContent, WeeklyReviewStats
from app.services.daily_briefing import _client, _as_utc

LOCAL_TIMEZONE = ZoneInfo("Europe/Oslo")
PROMPT_PATH = Path(__file__).parents[1] / "ai" / "prompts" / "weekly_review.md"
PROMPT_VERSION = "weekly-review-v1"
MAX_RETRY_MINUTES = 360
RETRY_BASE_MINUTES = 30


def last_complete_week_start(today: date | None = None) -> date:
    today = today or datetime.now(LOCAL_TIMEZONE).date()
    current_monday = today - timedelta(days=today.weekday())
    return current_monday - timedelta(days=7)


def build_weekly_stats(
    db: Session,
    owner_id: str,
    week_start: date,
) -> WeeklyReviewStats:
    week_end = week_start + timedelta(days=7)
    utc_start = datetime.combine(week_start, time.min, tzinfo=LOCAL_TIMEZONE).astimezone(UTC)
    utc_end = datetime.combine(week_end, time.min, tzinfo=LOCAL_TIMEZONE).astimezone(UTC)

    tasks_created = db.scalar(
        select(func.count(Task.id)).where(
            Task.owner_id == owner_id,
            Task.created_at >= utc_start,
            Task.created_at < utc_end,
        )
    ) or 0
    tasks_completed = db.scalar(
        select(func.count(Task.id)).where(
            Task.owner_id == owner_id,
            Task.completed_at >= utc_start,
            Task.completed_at < utc_end,
        )
    ) or 0
    tasks_with_deadlines = db.scalar(
        select(func.count(Task.id)).where(
            Task.owner_id == owner_id,
            Task.deadline >= week_start,
            Task.deadline < week_end,
        )
    ) or 0
    events = db.scalars(
        select(CalendarEvent).where(
            CalendarEvent.owner_id == owner_id,
            CalendarEvent.starts_at < utc_end,
            CalendarEvent.ends_at > utc_start,
            CalendarEvent.status != "cancelled",
        )
    ).all()
    scheduled_minutes = sum(
        max(
            0,
            int(
                (
                    min(_as_utc(event.ends_at), utc_end)
                    - max(_as_utc(event.starts_at), utc_start)
                ).total_seconds()
                // 60
            ),
        )
        for event in events
    )
    feedback_counts = db.execute(
        select(PreferenceFeedback.rating, func.count(PreferenceFeedback.id))
        .join(DailyBriefing, PreferenceFeedback.briefing_id == DailyBriefing.id)
        .where(
            PreferenceFeedback.owner_id == owner_id,
            DailyBriefing.owner_id == owner_id,
            DailyBriefing.local_date >= week_start,
            DailyBriefing.local_date < week_end,
        )
        .group_by(PreferenceFeedback.rating)
    ).all()
    counts = {rating: count for rating, count in feedback_counts}
    return WeeklyReviewStats(
        tasks_created=tasks_created,
        tasks_completed=tasks_completed,
        tasks_with_deadlines=tasks_with_deadlines,
        calendar_events=len(events),
        scheduled_minutes=scheduled_minutes,
        feedback_count=sum(counts.values()),
        helpful_feedback_count=counts.get(1, 0),
        unhelpful_feedback_count=counts.get(-1, 0),
    )


def fallback_review(stats: WeeklyReviewStats) -> WeeklyReviewContent:
    if stats.tasks_created == 0 and stats.tasks_completed == 0 and stats.calendar_events == 0:
        summary = "There is limited recorded task and calendar activity for this week."
    else:
        summary = (
            f"You recorded {stats.tasks_created} task(s) created and "
            f"{stats.tasks_completed} task(s) completed, with "
            f"{stats.calendar_events} calendar event(s)."
        )
    wins = (
        [f"Completed {stats.tasks_completed} task(s) during the week."]
        if stats.tasks_completed
        else []
    )
    suggested_focus = (
        ["Review upcoming task deadlines and choose a realistic next step."]
        if stats.tasks_with_deadlines
        else ["Choose one manageable priority for the coming week."]
    )
    return WeeklyReviewContent(
        summary=summary,
        wins=wins,
        reflection_question="What would you like to carry forward into next week?",
        suggested_focus=suggested_focus,
    )


def get_or_create_weekly_review(
    db: Session,
    owner_id: str,
    week_start: date | None = None,
    *,
    retry_pending: bool = False,
    force_retry: bool = False,
) -> WeeklyReview:
    week_start = week_start or last_complete_week_start()
    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")

    review = db.scalar(
        select(WeeklyReview).where(
            WeeklyReview.owner_id == owner_id,
            WeeklyReview.week_start == week_start,
        )
    )
    if review is not None and review.generation_status == "generated":
        return review
    if review is not None and not retry_pending:
        return review
    now = datetime.now(UTC)
    if (
        review is not None
        and not force_retry
        and review.next_retry_at is not None
        and _as_utc(review.next_retry_at) > now
    ):
        return review

    stats = build_weekly_stats(db, owner_id, week_start)
    fallback = fallback_review(stats)
    settings = get_settings()
    client = _client()
    attempt_count = (review.attempt_count if review is not None else 0) + 1
    error_message = "Ollama is not configured."
    generated_content = None
    if client is not None:
        try:
            prompt = PROMPT_PATH.read_text(encoding="utf-8")
            output = client.generate_json(
                system_prompt=prompt,
                context={
                    "week_start": week_start.isoformat(),
                    "week_end": (week_start + timedelta(days=6)).isoformat(),
                    "statistics": stats.model_dump(mode="json"),
                },
                schema=WeeklyReviewContent.model_json_schema(),
            )
            generated_content = WeeklyReviewContent.model_validate(output).model_dump(
                mode="json"
            )
            error_message = None
        except OllamaError as exc:
            error_message = str(exc)[:500]
        except OSError:
            error_message = "The versioned weekly review prompt could not be loaded."
        except ValidationError:
            error_message = "Ollama returned a weekly review that did not pass validation."

    if review is None:
        review = WeeklyReview(
            owner_id=owner_id,
            week_start=week_start,
            generation_status="pending",
            stats=stats.model_dump(mode="json"),
            content=fallback.model_dump(mode="json"),
            attempt_count=0,
        )
        db.add(review)
    review.stats = stats.model_dump(mode="json")
    review.attempt_count = attempt_count
    review.last_attempt_at = now
    if generated_content is not None:
        review.content = generated_content
        review.generation_status = "generated"
        review.model_name = settings.ollama_model
        review.generated_at = now
        review.error_message = None
        review.next_retry_at = None
    else:
        review.content = fallback.model_dump(mode="json")
        review.generation_status = "pending"
        review.model_name = None
        review.generated_at = None
        review.error_message = error_message
        review.next_retry_at = now + timedelta(
            minutes=min(
                RETRY_BASE_MINUTES * (2 ** min(attempt_count - 1, 4)),
                MAX_RETRY_MINUTES,
            )
        )
    db.commit()
    db.refresh(review)
    return review


def weekly_review_read(review: WeeklyReview) -> dict:
    return {
        "week_start": review.week_start,
        "week_end": review.week_start + timedelta(days=6),
        "generation_status": review.generation_status,
        "stats": review.stats,
        "content": review.content,
        "model_name": review.model_name,
        "generated_at": review.generated_at,
        "error_message": review.error_message,
        "attempt_count": review.attempt_count,
        "last_attempt_at": review.last_attempt_at,
        "next_retry_at": review.next_retry_at,
    }
