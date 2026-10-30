from datetime import date

from pydantic import Field

from app.schemas.personal import APIModel


class PlanningPriority(APIModel):
    task_id: str
    task_title: str
    score: int = Field(ge=0, le=100)
    reasons: list[str] = Field(max_length=8)
    deadline: date | None
    estimated_duration_minutes: int | None


class ProjectRecommendation(APIModel):
    project_id: str
    project_title: str
    score: int = Field(ge=0, le=100)
    reasons: list[str] = Field(max_length=8)


class ScheduleGap(APIModel):
    starts_at: str
    ends_at: str
    duration_minutes: int = Field(ge=0)


class ScheduleEvent(APIModel):
    title: str
    starts_at: str
    ends_at: str
    duration_minutes: int = Field(ge=0)


class ScheduleAnalysis(APIModel):
    event_count: int = Field(ge=0)
    events_truncated: bool
    scheduled_minutes: int = Field(ge=0)
    overlapping_event_count: int = Field(ge=0)
    calendar_gaps: list[ScheduleGap] = Field(max_length=51)
    events: list[ScheduleEvent] = Field(max_length=50)


class PlanningSnapshot(APIModel):
    local_date: date
    priorities: list[PlanningPriority] = Field(max_length=3)
    project_recommendations: list[ProjectRecommendation] = Field(max_length=3)
    schedule: ScheduleAnalysis
