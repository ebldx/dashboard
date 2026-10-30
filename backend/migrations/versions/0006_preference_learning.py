"""Add user feedback and reversible preference learning.

Revision ID: 0006_preference_learning
Revises: 0005_daily_briefings
Create Date: 2026-10-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_preference_learning"
down_revision: Union[str, None] = "0005_daily_briefings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "preference_feedback",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("briefing_id", sa.String(length=36), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["briefing_id"], ["daily_briefings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_id",
            "briefing_id",
            name="uq_preference_feedback_briefing",
        ),
    )
    op.create_index(
        op.f("ix_preference_feedback_owner_id"),
        "preference_feedback",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_preference_feedback_briefing_id"),
        "preference_feedback",
        ["briefing_id"],
        unique=False,
    )
    op.create_table(
        "preference_candidates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("feedback_id", sa.String(length=36), nullable=True),
        sa.Column("preference_field", sa.String(length=40), nullable=False),
        sa.Column("candidate_value", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("auto_applied", sa.Boolean(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["feedback_id"], ["preference_feedback.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "feedback_id",
            "preference_field",
            name="uq_preference_candidate_feedback_field",
        ),
    )
    op.create_index(
        op.f("ix_preference_candidates_owner_id"),
        "preference_candidates",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_preference_candidates_feedback_id"),
        "preference_candidates",
        ["feedback_id"],
        unique=False,
    )
    op.create_table(
        "preference_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=True),
        sa.Column("preference_field", sa.String(length=40), nullable=False),
        sa.Column("previous_value", sa.Text(), nullable=False),
        sa.Column("applied_value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["preference_candidates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id", name="uq_preference_history_candidate"),
    )
    op.create_index(
        op.f("ix_preference_history_owner_id"),
        "preference_history",
        ["owner_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_preference_history_owner_id"), table_name="preference_history")
    op.drop_table("preference_history")
    op.drop_index(op.f("ix_preference_candidates_feedback_id"), table_name="preference_candidates")
    op.drop_index(op.f("ix_preference_candidates_owner_id"), table_name="preference_candidates")
    op.drop_table("preference_candidates")
    op.drop_index(op.f("ix_preference_feedback_briefing_id"), table_name="preference_feedback")
    op.drop_index(op.f("ix_preference_feedback_owner_id"), table_name="preference_feedback")
    op.drop_table("preference_feedback")
