from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.ownership import DEFAULT_OWNER_ID
from app.db.models import (
    AcademicGoal,
    CalendarEvent,
    CareerGoal,
    Project,
    Task,
)
from app.schemas.planning import (
    PlanningPriority,
    PlanningSnapshot,
    ProjectRecommendation,
    ScheduleAnalysis,
    ScheduleEvent,
    ScheduleGap,
)

LOCAL_TIMEZONE = ZoneInfo("Europe/Oslo")
MAX_CANDIDATE_TASKS = 100
MAX_PROJECTS = 50
MAX_DAILY_PRIORITIES = 3
MAX_PROJECT_RECOMMENDATIONS = 3
MAX_CALENDAR_EVENTS = 50

PRIORITY_WEIGHTS = {"urgent": 35, "high": 27, "normal": 18, "low": 8}


def build_planning_snapshot(
    db: Session,
    owner_id: str = DEFAULT_OWNER_ID,
    today: date | None = None,
) -> PlanningSnapshot:
    today = today or datetime.now(LOCAL_TIMEZONE).date()
    day_start = datetime.combine(today, time.min, tzinfo=LOCAL_TIMEZONE).astimezone(UTC)
    day_end = datetime.combine(
        today + timedelta(days=1), time.min, tzinfo=LOCAL_TIMEZONE
    ).astimezone(UTC)

    career_goal_ids = set(
        db.scalars(
            select(CareerGoal.id).where(
                CareerGoal.owner_id == owner_id,
                CareerGoal.status == "active",
            )
        ).all()
    )
    academic_goal_ids = set(
        db.scalars(
            select(AcademicGoal.id).where(
                AcademicGoal.owner_id == owner_id,
                AcademicGoal.status == "active",
            )
        ).all()
    )
    active_goal_ids = career_goal_ids | academic_goal_ids
    projects = db.scalars(
        select(Project)
        .options(selectinload(Project.career_goals), selectinload(Project.academic_goals))
        .where(Project.owner_id == owner_id, Project.status == "active")
        .order_by(Project.importance.desc(), Project.target_date, Project.created_at)
        .limit(MAX_PROJECTS)
    ).all()
    project_task_counts = (
        dict(
            db.execute(
                select(Task.project_id, func.count(Task.id))
                .where(
                    Task.owner_id == owner_id,
                    Task.status.not_in(("completed", "cancelled")),
                    Task.project_id.in_([project.id for project in projects]),
                )
                .group_by(Task.project_id)
            ).all()
        )
        if projects
        else {}
    )
    tasks = db.scalars(
        select(Task)
        .where(
            Task.owner_id == owner_id,
            Task.status.not_in(("completed", "cancelled")),
        )
        .order_by(Task.deadline.is_(None), Task.deadline, Task.created_at)
        .limit(MAX_CANDIDATE_TASKS)
    ).all()
    project_goal_ids = {
        project.id: {
            goal.id for goal in (*project.career_goals, *project.academic_goals)
        }
        for project in projects
    }
    fetched_events = db.scalars(
        select(CalendarEvent)
        .where(
            CalendarEvent.owner_id == owner_id,
            CalendarEvent.starts_at < day_end,
            CalendarEvent.ends_at > day_start,
            CalendarEvent.status != "cancelled",
        )
        .order_by(CalendarEvent.starts_at)
        .limit(MAX_CALENDAR_EVENTS + 1)
    ).all()
    events_truncated = len(fetched_events) > MAX_CALENDAR_EVENTS
    events = fetched_events[:MAX_CALENDAR_EVENTS]

    priorities = [
        _score_task(task, today, active_goal_ids, project_goal_ids)
        for task in tasks
    ]
    priorities.sort(
        key=lambda item: (
            -item.score,
            item.deadline is None,
            item.deadline or date.max,
            item.task_title.casefold(),
        )
    )
    recommendations = [
        _score_project(
            project,
            today,
            active_goal_ids,
            project_task_counts.get(project.id, 0),
        )
        for project in projects
    ]
    recommendations.sort(
        key=lambda item: (-item.score, item.project_title.casefold())
    )

    return PlanningSnapshot(
        local_date=today,
        priorities=priorities[:MAX_DAILY_PRIORITIES],
        project_recommendations=recommendations[:MAX_PROJECT_RECOMMENDATIONS],
        schedule=_analyze_schedule(events, day_start, day_end, events_truncated),
    )


def _score_task(
    task: Task,
    today: date,
    active_goal_ids: set[str],
    project_goal_ids: dict[str, set[str]],
) -> PlanningPriority:
    reasons: list[str] = []
    score = PRIORITY_WEIGHTS.get(task.priority, 0)
    if task.priority != "normal":
        reasons.append(f"{task.priority.title()} task priority")

    if task.status == "in_progress":
        score += 5
        reasons.append("Already in progress")

    if task.deadline is not None:
        days_until_deadline = (task.deadline - today).days
        if days_until_deadline < 0:
            score += 40
            reasons.append(f"Overdue by {abs(days_until_deadline)} day(s)")
        elif days_until_deadline == 0:
            score += 35
            reasons.append("Due today")
        elif days_until_deadline <= 2:
            score += 27
            reasons.append(f"Due in {days_until_deadline} day(s)")
        elif days_until_deadline <= 7:
            score += 18
            reasons.append(f"Due within {days_until_deadline} days")
        elif days_until_deadline <= 14:
            score += 8
            reasons.append("Due within two weeks")

    linked_goal_ids = {
        goal_id
        for goal_id in (task.career_goal_id, task.academic_goal_id)
        if goal_id is not None
    }
    linked_project_goals = project_goal_ids.get(task.project_id, set())
    if linked_goal_ids & active_goal_ids or linked_project_goals & active_goal_ids:
        score += 15
        reasons.append("Supports an active goal")

    if not reasons:
        reasons.append("Open task available to plan")

    return PlanningPriority(
        task_id=task.id,
        task_title=task.title,
        score=min(score, 100),
        reasons=reasons,
        deadline=task.deadline,
        estimated_duration_minutes=task.estimated_duration_minutes,
    )


def _score_project(
    project: Project,
    today: date,
    active_goal_ids: set[str],
    open_task_count: int,
) -> ProjectRecommendation:
    score = project.importance * 10
    reasons = [f"Importance {project.importance} of 5"]
    linked_goal_ids = {
        goal.id for goal in (*project.career_goals, *project.academic_goals)
    }
    if linked_goal_ids & active_goal_ids:
        score += 20
        reasons.append("Supports an active goal")
    if open_task_count:
        score += 10
        reasons.append(f"Has {open_task_count} open task(s)")
    if project.target_date is not None:
        days_until_target = (project.target_date - today).days
        if days_until_target < 0:
            score += 15
            reasons.append("Target date has passed")
        elif days_until_target <= 7:
            score += 15
            reasons.append("Target date is within one week")
        elif days_until_target <= 30:
            score += 8
            reasons.append("Target date is within one month")
    return ProjectRecommendation(
        project_id=project.id,
        project_title=project.title,
        score=min(score, 100),
        reasons=reasons,
    )


def _analyze_schedule(
    events: list[CalendarEvent],
    day_start: datetime,
    day_end: datetime,
    events_truncated: bool,
) -> ScheduleAnalysis:
    event_intervals: list[tuple[datetime, datetime]] = []
    schedule_events: list[ScheduleEvent] = []
    for event in events:
        starts_at = _as_utc(event.starts_at)
        ends_at = _as_utc(event.ends_at)
        clipped_start = max(starts_at, day_start)
        clipped_end = min(ends_at, day_end)
        if clipped_end <= clipped_start:
            continue
        event_intervals.append((clipped_start, clipped_end))
        schedule_events.append(
            ScheduleEvent(
                title=event.title[:200],
                starts_at=starts_at.astimezone(LOCAL_TIMEZONE).isoformat(),
                ends_at=ends_at.astimezone(LOCAL_TIMEZONE).isoformat(),
                duration_minutes=max(0, int((clipped_end - clipped_start).total_seconds() // 60)),
            )
        )

    event_intervals.sort()
    merged: list[list[datetime]] = []
    overlapping_indices: set[int] = set()
    for left_index, (left_start, left_end) in enumerate(event_intervals):
        for right_index in range(left_index + 1, len(event_intervals)):
            right_start, right_end = event_intervals[right_index]
            if right_start >= left_end:
                break
            if left_start < right_end and right_start < left_end:
                overlapping_indices.update((left_index, right_index))
    for starts_at, ends_at in event_intervals:
        if merged and starts_at <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], ends_at)
        else:
            merged.append([starts_at, ends_at])

    gaps: list[ScheduleGap] = []
    cursor = day_start
    for starts_at, ends_at in merged:
        if starts_at > cursor:
            gaps.append(_gap(cursor, starts_at))
        cursor = max(cursor, ends_at)
    if cursor < day_end:
        gaps.append(_gap(cursor, day_end))

    scheduled_minutes = sum(
        int((ends_at - starts_at).total_seconds() // 60)
        for starts_at, ends_at in merged
    )
    return ScheduleAnalysis(
        event_count=len(schedule_events),
        events_truncated=events_truncated,
        scheduled_minutes=scheduled_minutes,
        overlapping_event_count=len(overlapping_indices),
        calendar_gaps=gaps,
        events=schedule_events,
    )


def _gap(starts_at: datetime, ends_at: datetime) -> ScheduleGap:
    return ScheduleGap(
        starts_at=starts_at.astimezone(LOCAL_TIMEZONE).isoformat(),
        ends_at=ends_at.astimezone(LOCAL_TIMEZONE).isoformat(),
        duration_minutes=int((ends_at - starts_at).total_seconds() // 60),
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
