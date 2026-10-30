from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Float,
    String,
    Table,
    Text,
    UniqueConstraint,
    Column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.core.ownership import DEFAULT_OWNER_ID


def new_id() -> str:
    return str(uuid4())


project_career_goals = Table(
    "project_career_goals",
    Base.metadata,
    Column("project_id", String(36), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("career_goal_id", String(36), ForeignKey("career_goals.id", ondelete="CASCADE"), primary_key=True),
)

project_academic_goals = Table(
    "project_academic_goals",
    Base.metadata,
    Column("project_id", String(36), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("academic_goal_id", String(36), ForeignKey("academic_goals.id", ondelete="CASCADE"), primary_key=True),
)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=DEFAULT_OWNER_ID
    )
    background: Mapped[str] = mapped_column(Text, default="", nullable=False)
    personal_story: Mapped[str] = mapped_column(Text, default="", nullable=False)
    interests: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    values: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    motivations: Mapped[str] = mapped_column(Text, default="", nullable=False)
    personality: Mapped[str] = mapped_column(Text, default="", nullable=False)
    work_environment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    communication_style: Mapped[str] = mapped_column(Text, default="", nullable=False)
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    technical_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    soft_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    development_areas: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    challenges: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    working_hours: Mapped[str] = mapped_column(Text, default="", nullable=False)
    study_sessions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    break_preferences: Mapped[str] = mapped_column(Text, default="", nullable=False)
    focus_preferences: Mapped[str] = mapped_column(Text, default="", nullable=False)
    planning_preferences: Mapped[str] = mapped_column(Text, default="", nullable=False)
    task_presentation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    response_detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    personal_objectives: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    desired_habits: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    self_improvement: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class CareerGoal(Base):
    __tablename__ = "career_goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    importance: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    time_horizon: Mapped[str] = mapped_column(String(40), default="unspecified", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class AcademicGoal(Base):
    __tablename__ = "academic_goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    programme: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    course: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    importance: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class PersonalPrinciple(Base):
    __tablename__ = "personal_principles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="general", nullable=False)
    importance: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    contexts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    frequency: Mapped[str] = mapped_column(String(30), default="sometimes", nullable=False)
    reminder: Mapped[str | None] = mapped_column(String(300), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class ResumeDocument(Base):
    __tablename__ = "resume_documents"
    __table_args__ = (
        UniqueConstraint("owner_id", "version", name="uq_resume_owner_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extraction_status: Mapped[str] = mapped_column(
        String(30), default="pending_review", nullable=False
    )
    facts: Mapped[list["ResumeFact"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ResumeFact.created_at",
    )


class ResumeFact(Base):
    __tablename__ = "resume_facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("resume_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    document: Mapped[ResumeDocument] = relationship(back_populates="facts")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    purpose: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="other", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    importance: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_effort_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_effort_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    acquired_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    career_goals: Mapped[list[CareerGoal]] = relationship(
        secondary=project_career_goals,
        order_by="CareerGoal.created_at",
    )
    academic_goals: Mapped[list[AcademicGoal]] = relationship(
        secondary=project_academic_goals,
        order_by="AcademicGoal.created_at",
    )
    milestones: Mapped[list["ProjectMilestone"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectMilestone.target_date, ProjectMilestone.created_at",
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project",
        order_by="Task.created_at.desc()",
    )


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    project: Mapped[Project] = relationship(back_populates="milestones")
    tasks: Mapped[list["Task"]] = relationship(back_populates="milestone")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="todo", nullable=False)
    priority: Mapped[str] = mapped_column(String(30), default="normal", nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str] = mapped_column(String(40), default="general", nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="user", nullable=False)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    milestone_id: Mapped[str | None] = mapped_column(
        ForeignKey("project_milestones.id", ondelete="SET NULL"), nullable=True, index=True
    )
    career_goal_id: Mapped[str | None] = mapped_column(
        ForeignKey("career_goals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    academic_goal_id: Mapped[str | None] = mapped_column(
        ForeignKey("academic_goals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    project: Mapped[Project | None] = relationship(back_populates="tasks")
    milestone: Mapped[ProjectMilestone | None] = relationship(back_populates="tasks")
    career_goal: Mapped[CareerGoal | None] = relationship()
    academic_goal: Mapped[AcademicGoal | None] = relationship()


class CalendarSource(Base):
    __tablename__ = "calendar_sources"
    __table_args__ = (
        UniqueConstraint("owner_id", "adapter", name="uq_calendar_source_owner_adapter"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    adapter: Mapped[str] = mapped_column(String(30), default="icalendar", nullable=False)
    display_name: Mapped[str] = mapped_column(
        String(100), default="Mine studier", nullable=False
    )
    feed_url_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    etag: Mapped[str | None] = mapped_column(String(500))
    last_modified: Mapped[str | None] = mapped_column(String(200))
    sync_status: Mapped[str] = mapped_column(
        String(30), default="never_synced", nullable=False
    )
    last_sync_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_sync_error: Mapped[str | None] = mapped_column(Text)
    last_event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_created_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_updated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_deleted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    events: Mapped[list["CalendarEvent"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
    )


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "source_uid",
            "occurrence_key",
            name="uq_calendar_event_source_identity",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("calendar_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_uid: Mapped[str] = mapped_column(String(500), nullable=False)
    occurrence_key: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    location: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    all_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_timezone: Mapped[str] = mapped_column(
        String(100), default="Europe/Oslo", nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), default="confirmed", nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    source: Mapped[CalendarSource] = relationship(back_populates="events")


class DailyBriefing(Base):
    __tablename__ = "daily_briefings"
    __table_args__ = (
        UniqueConstraint("owner_id", "local_date", name="uq_daily_briefing_owner_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    generation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class WeeklyReview(Base):
    __tablename__ = "weekly_reviews"
    __table_args__ = (
        UniqueConstraint("owner_id", "week_start", name="uq_weekly_review_owner_week"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    generation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    stats: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    content: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(200))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class PreferenceFeedback(Base):
    __tablename__ = "preference_feedback"
    __table_args__ = (
        UniqueConstraint("owner_id", "briefing_id", name="uq_preference_feedback_briefing"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    briefing_id: Mapped[str | None] = mapped_column(
        ForeignKey("daily_briefings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class PreferenceCandidate(Base):
    __tablename__ = "preference_candidates"
    __table_args__ = (
        UniqueConstraint(
            "feedback_id",
            "preference_field",
            name="uq_preference_candidate_feedback_field",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    feedback_id: Mapped[str | None] = mapped_column(
        ForeignKey("preference_feedback.id", ondelete="SET NULL"), nullable=True, index=True
    )
    preference_field: Mapped[str] = mapped_column(String(40), nullable=False)
    candidate_value: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    auto_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class PreferenceHistory(Base):
    __tablename__ = "preference_history"
    __table_args__ = (
        UniqueConstraint("candidate_id", name="uq_preference_history_candidate"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_OWNER_ID, nullable=False, index=True
    )
    candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("preference_candidates.id", ondelete="CASCADE"), nullable=True
    )
    preference_field: Mapped[str] = mapped_column(String(40), nullable=False)
    previous_value: Mapped[str] = mapped_column(Text, default="", nullable=False)
    applied_value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
