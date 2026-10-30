"""Add persistent weekly reviews and retry metadata.

Revision ID: 0007_scheduled_reviews
Revises: 0006_preference_learning
Create Date: 2026-10-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_scheduled_reviews"
down_revision: Union[str, None] = "0006_preference_learning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("daily_briefings") as batch_op:
        batch_op.add_column(
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("last_attempt_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("next_retry_at", sa.DateTime(timezone=True)))
        batch_op.alter_column("attempt_count", server_default=None)

    op.create_table(
        "weekly_reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("generation_status", sa.String(length=20), nullable=False),
        sa.Column("stats", sa.JSON(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "week_start", name="uq_weekly_review_owner_week"),
    )
    op.create_index(
        op.f("ix_weekly_reviews_owner_id"),
        "weekly_reviews",
        ["owner_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_weekly_reviews_owner_id"), table_name="weekly_reviews")
    op.drop_table("weekly_reviews")
    with op.batch_alter_table("daily_briefings") as batch_op:
        batch_op.drop_column("next_retry_at")
        batch_op.drop_column("last_attempt_at")
        batch_op.drop_column("attempt_count")
