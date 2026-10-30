"""Add profile, goals, principles, and resume records.

Revision ID: 0002_personal_information
Revises: 0001_system_settings
Create Date: 2026-10-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_personal_information"
down_revision: Union[str, None] = "0001_system_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("background", sa.Text(), nullable=False),
        sa.Column("personal_story", sa.Text(), nullable=False),
        sa.Column("interests", sa.JSON(), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("motivations", sa.Text(), nullable=False),
        sa.Column("personality", sa.Text(), nullable=False),
        sa.Column("work_environment", sa.Text(), nullable=False),
        sa.Column("communication_style", sa.Text(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("technical_skills", sa.JSON(), nullable=False),
        sa.Column("soft_skills", sa.JSON(), nullable=False),
        sa.Column("development_areas", sa.JSON(), nullable=False),
        sa.Column("challenges", sa.JSON(), nullable=False),
        sa.Column("working_hours", sa.Text(), nullable=False),
        sa.Column("study_sessions", sa.Text(), nullable=False),
        sa.Column("break_preferences", sa.Text(), nullable=False),
        sa.Column("focus_preferences", sa.Text(), nullable=False),
        sa.Column("planning_preferences", sa.Text(), nullable=False),
        sa.Column("task_presentation", sa.Text(), nullable=False),
        sa.Column("response_detail", sa.Text(), nullable=False),
        sa.Column("personal_objectives", sa.JSON(), nullable=False),
        sa.Column("desired_habits", sa.JSON(), nullable=False),
        sa.Column("self_improvement", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "career_goals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("time_horizon", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("required_skills", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_career_goals_owner_id"),
        "career_goals",
        ["owner_id"],
        unique=False,
    )
    op.create_table(
        "academic_goals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("programme", sa.String(length=200), nullable=False),
        sa.Column("course", sa.String(length=200), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_academic_goals_owner_id"),
        "academic_goals",
        ["owner_id"],
        unique=False,
    )
    op.create_table(
        "personal_principles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("contexts", sa.JSON(), nullable=False),
        sa.Column("frequency", sa.String(length=30), nullable=False),
        sa.Column("reminder", sa.String(length=300), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_personal_principles_owner_id"),
        "personal_principles",
        ["owner_id"],
        unique=False,
    )
    op.create_table(
        "resume_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=100), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extraction_status", sa.String(length=30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "version", name="uq_resume_owner_version"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        op.f("ix_resume_documents_owner_id"),
        "resume_documents",
        ["owner_id"],
        unique=False,
    )
    op.create_table(
        "resume_facts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["resume_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_resume_facts_document_id"),
        "resume_facts",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_resume_facts_document_id"), table_name="resume_facts")
    op.drop_table("resume_facts")
    op.drop_index(op.f("ix_resume_documents_owner_id"), table_name="resume_documents")
    op.drop_table("resume_documents")
    op.drop_index(op.f("ix_personal_principles_owner_id"), table_name="personal_principles")
    op.drop_table("personal_principles")
    op.drop_index(op.f("ix_academic_goals_owner_id"), table_name="academic_goals")
    op.drop_table("academic_goals")
    op.drop_index(op.f("ix_career_goals_owner_id"), table_name="career_goals")
    op.drop_table("career_goals")
    op.drop_table("user_profiles")
