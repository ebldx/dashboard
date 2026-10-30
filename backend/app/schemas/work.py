from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.personal import APIModel

ProjectCategory = Literal[
    "academic",
    "career_development",
    "technical",
    "personal_development",
    "creative",
    "other",
]
ProjectStatus = Literal["active", "paused", "completed", "archived"]
MilestoneStatus = Literal["pending", "completed", "cancelled"]
TaskStatus = Literal["todo", "in_progress", "completed", "cancelled"]
TaskPriority = Literal["low", "normal", "high", "urgent"]
TaskCategory = Literal[
    "academic",
    "career",
    "personal",
    "projects",
    "administrative",
    "general",
]


class ProjectCreate(APIModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    purpose: str = Field(default="", max_length=5000)
    category: ProjectCategory = "other"
    status: ProjectStatus = "active"
    importance: int = Field(default=3, ge=1, le=5)
    start_date: date | None = None
    target_date: date | None = None
    estimated_effort_hours: float | None = Field(default=None, ge=0, le=100000)
    actual_effort_hours: float | None = Field(default=None, ge=0, le=100000)
    notes: str = Field(default="", max_length=20000)
    acquired_skills: list[str] = Field(default_factory=list, max_length=100)
    career_goal_ids: list[str] = Field(default_factory=list, max_length=100)
    academic_goal_ids: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_date_order(self) -> "ProjectCreate":
        if self.start_date and self.target_date and self.target_date < self.start_date:
            raise ValueError("target_date cannot be before start_date")
        return self


class ProjectPatch(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    purpose: str | None = Field(default=None, max_length=5000)
    category: ProjectCategory | None = None
    status: ProjectStatus | None = None
    importance: int | None = Field(default=None, ge=1, le=5)
    start_date: date | None = None
    target_date: date | None = None
    estimated_effort_hours: float | None = Field(default=None, ge=0, le=100000)
    actual_effort_hours: float | None = Field(default=None, ge=0, le=100000)
    notes: str | None = Field(default=None, max_length=20000)
    acquired_skills: list[str] | None = Field(default=None, max_length=100)
    career_goal_ids: list[str] | None = Field(default=None, max_length=100)
    academic_goal_ids: list[str] | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_date_order(self) -> "ProjectPatch":
        if self.start_date and self.target_date and self.target_date < self.start_date:
            raise ValueError("target_date cannot be before start_date")
        return self


class ProjectRead(APIModel):
    id: str
    title: str
    description: str
    purpose: str
    category: ProjectCategory
    status: ProjectStatus
    importance: int
    start_date: date | None
    target_date: date | None
    estimated_effort_hours: float | None
    actual_effort_hours: float | None
    notes: str
    acquired_skills: list[str]
    career_goal_ids: list[str]
    academic_goal_ids: list[str]
    career_goal_titles: list[str]
    academic_goal_titles: list[str]
    milestone_count: int
    completed_milestone_count: int
    task_count: int
    completed_task_count: int
    progress_percent: int
    created_at: datetime
    updated_at: datetime


class MilestoneCreate(APIModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    target_date: date | None = None
    status: MilestoneStatus = "pending"


class MilestonePatch(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    target_date: date | None = None
    status: MilestoneStatus | None = None


class MilestoneRead(APIModel):
    id: str
    project_id: str
    title: str
    description: str
    target_date: date | None
    status: MilestoneStatus
    completed_at: datetime | None
    task_count: int
    completed_task_count: int
    created_at: datetime
    updated_at: datetime


class TaskCreate(APIModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    status: TaskStatus = "todo"
    priority: TaskPriority = "normal"
    deadline: date | None = None
    estimated_duration_minutes: int | None = Field(default=None, ge=0, le=525600)
    actual_duration_minutes: int | None = Field(default=None, ge=0, le=525600)
    category: TaskCategory = "general"
    project_id: str | None = None
    milestone_id: str | None = None
    career_goal_id: str | None = None
    academic_goal_id: str | None = None

    @model_validator(mode="after")
    def validate_relationships(self) -> "TaskCreate":
        if self.milestone_id and not self.project_id:
            raise ValueError("project_id is required when milestone_id is set")
        return self


class TaskPatch(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    deadline: date | None = None
    estimated_duration_minutes: int | None = Field(default=None, ge=0, le=525600)
    actual_duration_minutes: int | None = Field(default=None, ge=0, le=525600)
    category: TaskCategory | None = None
    project_id: str | None = None
    milestone_id: str | None = None
    career_goal_id: str | None = None
    academic_goal_id: str | None = None

    @model_validator(mode="after")
    def validate_relationships(self) -> "TaskPatch":
        if self.milestone_id and self.project_id is None:
            raise ValueError("project_id must be provided when changing milestone_id")
        return self


class TaskRead(APIModel):
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    deadline: date | None
    estimated_duration_minutes: int | None
    actual_duration_minutes: int | None
    category: TaskCategory
    source: Literal["user"]
    project_id: str | None
    project_title: str | None
    milestone_id: str | None
    milestone_title: str | None
    career_goal_id: str | None
    career_goal_title: str | None
    academic_goal_id: str | None
    academic_goal_title: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
