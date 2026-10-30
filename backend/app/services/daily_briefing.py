from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.ai.ollama import OllamaClient, OllamaError
from app.core.config import get_settings
from app.db.models import (
    AcademicGoal,
    CalendarEvent,
    CareerGoal,
    DailyBriefing,
    PersonalPrinciple,
    Project,
    Task,
    UserProfile,
)
from app.schemas.ai import BriefingContent
from app.services.planning import build_planning_snapshot

BRIEFING_PROMPT_VERSION = "daily-briefing-v2"
PROMPT_PATH = Path(__file__).parents[1] / "ai" / "prompts" / "daily_briefing.md"
LOCAL_TIMEZONE = ZoneInfo("Europe/Oslo")
MAX_TASKS = 30
MAX_EVENTS = 50
MAX_GOALS = 10
MAX_PRINCIPLES = 10
RETRY_BASE_MINUTES = 30
RETRY_MAX_MINUTES = 360


def build_context(db: Session, owner_id: str, today: date) -> dict:
    start = datetime.combine(today, time.min, tzinfo=LOCAL_TIMEZONE).astimezone(UTC)
    end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=LOCAL_TIMEZONE).astimezone(
        UTC
    )
    tasks = db.scalars(
        select(Task)
        .where(
            Task.owner_id == owner_id,
            Task.status.not_in(("completed", "cancelled")),
        )
        .order_by(
            Task.deadline.is_(None),
            Task.deadline,
            case(
                (Task.priority == "urgent", 4),
                (Task.priority == "high", 3),
                (Task.priority == "normal", 2),
                (Task.priority == "low", 1),
                else_=0,
            ).desc(),
            Task.created_at,
        )
        .limit(MAX_TASKS)
    ).all()
    events = db.scalars(
        select(CalendarEvent)
        .where(
            CalendarEvent.owner_id == owner_id,
            CalendarEvent.starts_at < end,
            CalendarEvent.ends_at > start,
            CalendarEvent.status != "cancelled",
        )
        .order_by(CalendarEvent.starts_at)
        .limit(MAX_EVENTS)
    ).all()
    career_goals = db.scalars(
        select(CareerGoal)
        .where(CareerGoal.owner_id == owner_id, CareerGoal.status == "active")
        .order_by(CareerGoal.importance.desc(), CareerGoal.created_at.desc())
        .limit(MAX_GOALS)
    ).all()
    academic_goals = db.scalars(
        select(AcademicGoal)
        .where(AcademicGoal.owner_id == owner_id, AcademicGoal.status == "active")
        .order_by(AcademicGoal.importance.desc(), AcademicGoal.created_at.desc())
        .limit(MAX_GOALS)
    ).all()
    principles = db.scalars(
        select(PersonalPrinciple)
        .where(
            PersonalPrinciple.owner_id == owner_id,
            PersonalPrinciple.active.is_(True),
        )
        .order_by(PersonalPrinciple.importance.desc(), PersonalPrinciple.created_at)
        .limit(MAX_PRINCIPLES)
    ).all()
    projects = {
        project.id: project
        for project in db.scalars(select(Project).where(Project.owner_id == owner_id)).all()
    }
    profile = db.get(UserProfile, owner_id)

    planning = build_planning_snapshot(db, owner_id, today)
    return {
        "date": today.isoformat(),
        "tasks": [
            {
                "id": task.id,
                "title": task.title[:200],
                "status": task.status,
                "priority": task.priority,
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "project": (
                    projects[task.project_id].title[:120]
                    if task.project_id in projects
                    else None
                ),
            }
            for task in tasks
        ],
        "events": [
            {
                "title": event.title[:200],
                "starts_at": _as_utc(event.starts_at).astimezone(LOCAL_TIMEZONE).isoformat(),
                "ends_at": _as_utc(event.ends_at).astimezone(LOCAL_TIMEZONE).isoformat(),
            }
            for event in events
        ],
        "goals": [
            {"id": goal.id, "kind": "career", "title": goal.title[:200]}
            for goal in career_goals
        ]
        + [
            {"id": goal.id, "kind": "academic", "title": goal.title[:200]}
            for goal in academic_goals
        ],
        "principles": [
            {
                "id": principle.id,
                "title": principle.title[:120],
                "description": principle.description[:300],
                "reminder": principle.reminder[:300] if principle.reminder else None,
            }
            for principle in principles
        ],
        "preferences": {
            "focus": profile.focus_preferences[:500],
            "planning": profile.planning_preferences[:500],
            "breaks": profile.break_preferences[:500],
        }
        if profile
        else {},
        "planning": planning.model_dump(mode="json"),
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _fallback(context: dict) -> BriefingContent:
    events = context["events"]
    tasks = context["tasks"]
    if events or tasks:
        overview = (
            f"You have {len(events)} calendar commitment"
            f"{'' if len(events) == 1 else 's'} and {len(tasks)} open task"
            f"{'' if len(tasks) == 1 else 's'} in today's planning context."
        )
    else:
        overview = "There is not enough information for a personalized briefing today."
    return BriefingContent(
        overview=overview,
        priorities=[],
        principle_reminders=[],
        focus_advice="Review your commitments and choose a manageable next step.",
    )


def _client() -> OllamaClient | None:
    settings = get_settings()
    if not settings.ollama_base_url or not settings.ollama_model:
        return None
    return OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )


def get_ollama_status() -> dict:
    settings = get_settings()
    client = _client()
    if client is None:
        return {
            "configured": False,
            "reachable": False,
            "model_configured": bool(settings.ollama_model),
            "model_available": False,
            "model_name": settings.ollama_model,
            "status": "not_configured",
        }
    try:
        models = client.get_installed_models()
    except OllamaError:
        return {
            "configured": True,
            "reachable": False,
            "model_configured": True,
            "model_available": False,
            "model_name": settings.ollama_model,
            "status": "unavailable",
        }
    model_available = settings.ollama_model in models or f"{settings.ollama_model}:latest" in models
    return {
        "configured": True,
        "reachable": True,
        "model_configured": True,
        "model_available": model_available,
        "model_name": settings.ollama_model,
        "status": "ready" if model_available else "model_missing",
    }


def get_or_create_briefing(
    db: Session,
    owner_id: str,
    today: date | None = None,
    *,
    retry_pending: bool = False,
    force_retry: bool = False,
) -> DailyBriefing:
    today = today or datetime.now(LOCAL_TIMEZONE).date()
    briefing = db.scalar(
        select(DailyBriefing).where(
            DailyBriefing.owner_id == owner_id,
            DailyBriefing.local_date == today,
        )
    )
    if briefing is not None and briefing.generation_status == "generated":
        return briefing
    if briefing is not None and not retry_pending:
        return briefing
    now = datetime.now(UTC)
    if (
        briefing is not None
        and not force_retry
        and briefing.next_retry_at is not None
        and _as_utc(briefing.next_retry_at) > now
    ):
        return briefing

    context = build_context(db, owner_id, today)
    fallback = _fallback(context)
    settings = get_settings()
    client = _client()
    attempt_count = (briefing.attempt_count if briefing is not None else 0) + 1
    error_message = "Ollama is not configured."
    generated_content = None
    if client is not None:
        try:
            prompt = PROMPT_PATH.read_text(encoding="utf-8")
            output = client.generate_json(
                system_prompt=prompt,
                context=context,
                schema=BriefingContent.model_json_schema(),
            )
            validated = BriefingContent.model_validate(output)
            _validate_references(validated, context)
            generated_content = validated.model_dump(mode="json")
            error_message = None
        except OllamaError as exc:
            error_message = str(exc)[:500]
        except OSError:
            error_message = "The versioned briefing prompt could not be loaded."
        except (ValidationError, ValueError):
            error_message = "Ollama returned a briefing that did not pass validation."

    if briefing is None:
        briefing = DailyBriefing(
            owner_id=owner_id,
            local_date=today,
            generation_status="pending",
            content=fallback.model_dump(mode="json"),
            prompt_version=BRIEFING_PROMPT_VERSION,
        )
        db.add(briefing)
    briefing.attempt_count = attempt_count
    briefing.last_attempt_at = now
    if generated_content is not None:
        briefing.content = generated_content
        briefing.generation_status = "generated"
        briefing.model_name = settings.ollama_model
        briefing.generated_at = datetime.now(UTC)
        briefing.error_message = None
        briefing.next_retry_at = None
    else:
        briefing.content = fallback.model_dump(mode="json")
        briefing.generation_status = "pending"
        briefing.model_name = None
        briefing.generated_at = None
        briefing.error_message = error_message
        briefing.next_retry_at = now + timedelta(
            minutes=min(
                RETRY_BASE_MINUTES * (2 ** min(attempt_count - 1, 4)),
                RETRY_MAX_MINUTES,
            )
        )
    db.commit()
    db.refresh(briefing)
    return briefing


def _validate_references(content: BriefingContent, context: dict) -> None:
    tasks = {task["id"]: task for task in context["tasks"]}
    principles = {principle["id"]: principle for principle in context["principles"]}
    for item in content.priorities:
        if item.task_id not in tasks:
            raise ValueError("Briefing references an unknown task")
        item.task_title = tasks[item.task_id]["title"]
    for item in content.principle_reminders:
        if item.principle_id not in principles:
            raise ValueError("Briefing references an unknown principle")
        item.principle_title = principles[item.principle_id]["title"]
    projects = {
        project["project_id"]: project
        for project in context["planning"]["project_recommendations"]
    }
    for item in content.project_recommendations:
        if item.project_id not in projects:
            raise ValueError("Briefing references an unknown recommended project")
        item.project_title = projects[item.project_id]["project_title"]
