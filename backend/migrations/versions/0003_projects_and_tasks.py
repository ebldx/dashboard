"""Add projects, milestones, tasks, and goal relationships.

Revision ID: 0003_projects_and_tasks
Revises: 0002_personal_information
Create Date: 2026-10-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_projects_and_tasks"
down_revision: Union[str, None] = "0002_personal_information"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("estimated_effort_hours", sa.Float(), nullable=True),
        sa.Column("actual_effort_hours", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("acquired_skills", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"], unique=False)

    op.create_table(
        "project_milestones",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_project_milestones_owner_id"),
        "project_milestones",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_milestones_project_id"),
        "project_milestones",
        ["project_id"],
        unique=False,
    )

    op.create_table(
        "project_career_goals",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("career_goal_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["career_goal_id"], ["career_goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", "career_goal_id"),
    )
    op.create_table(
        "project_academic_goals",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("academic_goal_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["academic_goal_id"], ["academic_goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", "academic_goal_id"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("priority", sa.String(length=30), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("actual_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("milestone_id", sa.String(length=36), nullable=True),
        sa.Column("career_goal_id", sa.String(length=36), nullable=True),
        sa.Column("academic_goal_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["academic_goal_id"], ["academic_goals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["career_goal_id"], ["career_goals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["milestone_id"], ["project_milestones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "owner_id",
        "deadline",
        "project_id",
        "milestone_id",
        "career_goal_id",
        "academic_goal_id",
    ):
        op.create_index(op.f(f"ix_tasks_{column}"), "tasks", [column], unique=False)


def downgrade() -> None:
    for column in (
        "owner_id",
        "deadline",
        "project_id",
        "milestone_id",
        "career_goal_id",
        "academic_goal_id",
    ):
        op.drop_index(op.f(f"ix_tasks_{column}"), table_name="tasks")
    op.drop_table("tasks")
    op.drop_table("project_academic_goals")
    op.drop_table("project_career_goals")
    op.drop_index(op.f("ix_project_milestones_project_id"), table_name="project_milestones")
    op.drop_index(op.f("ix_project_milestones_owner_id"), table_name="project_milestones")
    op.drop_table("project_milestones")
    op.drop_index(op.f("ix_projects_owner_id"), table_name="projects")
    op.drop_table("projects")
