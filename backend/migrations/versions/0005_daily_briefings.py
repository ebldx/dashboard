"""Add validated daily AI briefings.

Revision ID: 0005_daily_briefings
Revises: 0004_calendar_integration
Create Date: 2026-10-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_daily_briefings"
down_revision: Union[str, None] = "0004_calendar_integration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_briefings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("generation_status", sa.String(length=20), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "local_date", name="uq_daily_briefing_owner_date"),
    )
    op.create_index(
        op.f("ix_daily_briefings_owner_id"),
        "daily_briefings",
        ["owner_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_daily_briefings_owner_id"), table_name="daily_briefings")
    op.drop_table("daily_briefings")
