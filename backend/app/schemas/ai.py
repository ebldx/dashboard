from datetime import date, datetime
from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from app.schemas.personal import APIModel


class BriefingPriority(APIModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid",
    )

    task_id: str = Field(min_length=1, max_length=36)
    task_title: str | None = Field(default=None, max_length=200)
    reason: str = Field(min_length=1, max_length=400)


class BriefingPrinciple(APIModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid",
    )

    principle_id: str = Field(min_length=1, max_length=36)
    principle_title: str | None = Field(default=None, max_length=120)
    reminder: str = Field(min_length=1, max_length=400)


class BriefingProjectRecommendation(APIModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid",
    )

    project_id: str = Field(min_length=1, max_length=36)
    project_title: str | None = Field(default=None, max_length=200)
    reason: str = Field(min_length=1, max_length=400)


class BriefingContent(APIModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid",
    )

    overview: str = Field(min_length=1, max_length=2000)
    priorities: list[BriefingPriority] = Field(default_factory=list, max_length=3)
    principle_reminders: list[BriefingPrinciple] = Field(
        default_factory=list, max_length=2
    )
    project_recommendations: list[BriefingProjectRecommendation] = Field(
        default_factory=list,
        max_length=3,
    )
    focus_advice: str = Field(min_length=1, max_length=1000)

    @field_validator("priorities")
    @classmethod
    def unique_priority_tasks(
        cls, value: list[BriefingPriority]
    ) -> list[BriefingPriority]:
        task_ids = [item.task_id for item in value]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("A task can only appear once in the priority list")
        return value

    @field_validator("principle_reminders")
    @classmethod
    def unique_principles(
        cls, value: list[BriefingPrinciple]
    ) -> list[BriefingPrinciple]:
        principle_ids = [item.principle_id for item in value]
        if len(principle_ids) != len(set(principle_ids)):
            raise ValueError("A principle can only appear once")
        return value


class DailyBriefingRead(APIModel):
    local_date: date
    generation_status: Literal["pending", "generated"]
    content: BriefingContent
    model_name: str | None
    prompt_version: str
    generated_at: datetime | None
    updated_at: datetime
    error_message: str | None
    attempt_count: int
    last_attempt_at: datetime | None
    next_retry_at: datetime | None


class WeeklyReviewContent(APIModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid",
    )

    summary: str = Field(min_length=1, max_length=1500)
    wins: list[str] = Field(default_factory=list, max_length=5)
    reflection_question: str = Field(min_length=1, max_length=500)
    suggested_focus: list[str] = Field(default_factory=list, max_length=3)


class WeeklyReviewStats(APIModel):
    tasks_created: int = Field(ge=0)
    tasks_completed: int = Field(ge=0)
    tasks_with_deadlines: int = Field(ge=0)
    calendar_events: int = Field(ge=0)
    scheduled_minutes: int = Field(ge=0)
    feedback_count: int = Field(ge=0)
    helpful_feedback_count: int = Field(ge=0)
    unhelpful_feedback_count: int = Field(ge=0)


class WeeklyReviewRead(APIModel):
    week_start: date
    week_end: date
    generation_status: Literal["pending", "generated"]
    stats: WeeklyReviewStats
    content: WeeklyReviewContent
    model_name: str | None
    generated_at: datetime | None
    error_message: str | None
    attempt_count: int
    last_attempt_at: datetime | None
    next_retry_at: datetime | None


class OllamaStatus(APIModel):
    configured: bool
    reachable: bool
    model_configured: bool
    model_available: bool
    model_name: str | None
    status: Literal["not_configured", "unavailable", "model_missing", "ready"]
