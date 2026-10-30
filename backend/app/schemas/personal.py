from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GoalStatus = Literal["active", "paused", "completed", "archived"]
TimeHorizon = Literal["short_term", "medium_term", "long_term", "unspecified"]
PrincipleCategory = Literal[
    "productivity",
    "learning",
    "wellbeing",
    "personal_growth",
    "career",
    "academic",
    "projects",
    "general",
]
Frequency = Literal["daily", "weekly", "sometimes", "occasionally"]
FactCategory = Literal[
    "contact",
    "experience",
    "education",
    "skill",
    "certification",
    "language",
    "project",
    "achievement",
    "responsibility",
    "interest",
    "other",
]


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class ProfilePatch(APIModel):
    background: str = Field(default="", max_length=5000)
    personal_story: str = Field(default="", max_length=10000)
    interests: list[str] = Field(default_factory=list, max_length=100)
    values: list[str] = Field(default_factory=list, max_length=100)
    motivations: str = Field(default="", max_length=5000)
    personality: str = Field(default="", max_length=5000)
    work_environment: str = Field(default="", max_length=3000)
    communication_style: str = Field(default="", max_length=3000)
    strengths: list[str] = Field(default_factory=list, max_length=100)
    technical_skills: list[str] = Field(default_factory=list, max_length=100)
    soft_skills: list[str] = Field(default_factory=list, max_length=100)
    development_areas: list[str] = Field(default_factory=list, max_length=100)
    challenges: list[str] = Field(default_factory=list, max_length=100)
    working_hours: str = Field(default="", max_length=2000)
    study_sessions: str = Field(default="", max_length=2000)
    break_preferences: str = Field(default="", max_length=2000)
    focus_preferences: str = Field(default="", max_length=2000)
    planning_preferences: str = Field(default="", max_length=2000)
    task_presentation: str = Field(default="", max_length=2000)
    response_detail: str = Field(default="", max_length=2000)
    personal_objectives: list[str] = Field(default_factory=list, max_length=100)
    desired_habits: list[str] = Field(default_factory=list, max_length=100)
    self_improvement: list[str] = Field(default_factory=list, max_length=100)


class ProfileRead(ProfilePatch):
    id: str
    updated_at: datetime | None = None


class CareerGoalCreate(APIModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    importance: int = Field(default=3, ge=1, le=5)
    time_horizon: TimeHorizon = "unspecified"
    status: GoalStatus = "active"
    required_skills: list[str] = Field(default_factory=list, max_length=100)


class CareerGoalPatch(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    importance: int | None = Field(default=None, ge=1, le=5)
    time_horizon: TimeHorizon | None = None
    status: GoalStatus | None = None
    required_skills: list[str] | None = Field(default=None, max_length=100)


class CareerGoalRead(CareerGoalCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class AcademicGoalCreate(APIModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    programme: str = Field(default="", max_length=200)
    course: str = Field(default="", max_length=200)
    target_date: date | None = None
    importance: int = Field(default=3, ge=1, le=5)
    status: GoalStatus = "active"


class AcademicGoalPatch(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    programme: str | None = Field(default=None, max_length=200)
    course: str | None = Field(default=None, max_length=200)
    target_date: date | None = None
    importance: int | None = Field(default=None, ge=1, le=5)
    status: GoalStatus | None = None


class AcademicGoalRead(AcademicGoalCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class PrincipleCreate(APIModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    category: PrincipleCategory = "general"
    importance: int = Field(default=3, ge=1, le=5)
    contexts: list[str] = Field(default_factory=list, max_length=100)
    frequency: Frequency = "sometimes"
    reminder: str | None = Field(default=None, max_length=300)
    active: bool = True


class PrinciplePatch(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    category: PrincipleCategory | None = None
    importance: int | None = Field(default=None, ge=1, le=5)
    contexts: list[str] | None = Field(default=None, max_length=100)
    frequency: Frequency | None = None
    reminder: str | None = Field(default=None, max_length=300)
    active: bool | None = None


class PrincipleRead(PrincipleCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class ResumeFactPatch(APIModel):
    category: FactCategory | None = None
    value: str | None = Field(default=None, min_length=1, max_length=5000)
    verified: bool | None = None


class ResumeFactRead(APIModel):
    id: str
    document_id: str
    category: FactCategory
    value: str
    verified: bool
    created_at: datetime
    updated_at: datetime


class ResumeDocumentRead(APIModel):
    id: str
    original_filename: str
    media_type: str
    file_size: int
    version: int
    uploaded_at: datetime
    extracted_at: datetime | None
    extraction_status: str
    facts: list[ResumeFactRead] = Field(default_factory=list)


class ResumeDocumentSummary(APIModel):
    id: str
    original_filename: str
    media_type: str
    file_size: int
    version: int
    uploaded_at: datetime
    extracted_at: datetime | None
    extraction_status: str
    fact_count: int
    verified_fact_count: int
