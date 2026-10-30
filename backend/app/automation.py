import argparse
import logging
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select

from app.core.ownership import DEFAULT_OWNER_ID
from app.db.models import DailyBriefing, WeeklyReview
from app.db.session import SessionLocal
from app.services.daily_briefing import get_or_create_briefing
from app.services.weekly_review import (
    get_or_create_weekly_review,
    last_complete_week_start,
)

logger = logging.getLogger("daymark.automation")
LOCAL_TIMEZONE = ZoneInfo("Europe/Oslo")


def run_daily_briefing(
    local_date: date | None = None,
    *,
    retry_pending: bool = True,
) -> int:
    with SessionLocal() as session:
        briefing = get_or_create_briefing(
            session,
            DEFAULT_OWNER_ID,
            local_date,
            retry_pending=retry_pending,
        )
    logger.info(
        "daily_briefing date=%s status=%s attempts=%d next_retry_at=%s",
        briefing.local_date,
        briefing.generation_status,
        briefing.attempt_count,
        briefing.next_retry_at,
    )
    return 0


def run_retry_daily() -> int:
    today = datetime.now(LOCAL_TIMEZONE).date()
    with SessionLocal() as session:
        pending_date = session.scalar(
            select(DailyBriefing.local_date)
            .where(
                DailyBriefing.owner_id == DEFAULT_OWNER_ID,
                DailyBriefing.generation_status == "pending",
                DailyBriefing.local_date <= today,
                (DailyBriefing.next_retry_at.is_(None))
                | (DailyBriefing.next_retry_at <= datetime.now(UTC)),
            )
            .order_by(DailyBriefing.local_date.desc())
            .limit(1)
        )
    if pending_date is None:
        logger.info("daily_retry no pending briefing is due")
        return 0
    return run_daily_briefing(pending_date, retry_pending=True)


def run_weekly_review(week_start: date | None = None) -> int:
    week_start = week_start or last_complete_week_start()
    with SessionLocal() as session:
        review = get_or_create_weekly_review(
            session,
            DEFAULT_OWNER_ID,
            week_start,
            retry_pending=True,
        )
    logger.info(
        "weekly_review week_start=%s status=%s attempts=%d next_retry_at=%s",
        review.week_start,
        review.generation_status,
        review.attempt_count,
        review.next_retry_at,
    )
    return 0


def run_retry_weekly() -> int:
    with SessionLocal() as session:
        week_start = session.scalar(
            select(WeeklyReview.week_start)
            .where(
                WeeklyReview.owner_id == DEFAULT_OWNER_ID,
                WeeklyReview.generation_status == "pending",
                (WeeklyReview.next_retry_at.is_(None))
                | (WeeklyReview.next_retry_at <= datetime.now(UTC)),
            )
            .order_by(WeeklyReview.week_start)
            .limit(1)
        )
    if week_start is None:
        logger.info("weekly_retry no pending review is due")
        return 0
    return run_weekly_review(week_start)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate idempotent daily briefings and weekly reviews."
    )
    parser.add_argument(
        "job",
        choices=("daily-briefing", "retry-daily", "weekly-review", "retry-weekly"),
        help="Scheduled job to run. Retry jobs respect the persisted backoff window.",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if args.job == "daily-briefing":
        return run_daily_briefing()
    if args.job == "retry-daily":
        now = datetime.now(LOCAL_TIMEZONE)
        if not (7 <= now.hour <= 23):
            logger.info("daily_retry outside local retry window; skipping")
            return 0
        return run_retry_daily()
    if args.job == "retry-weekly":
        return run_retry_weekly()
    return run_weekly_review()


if __name__ == "__main__":
    raise SystemExit(main())
