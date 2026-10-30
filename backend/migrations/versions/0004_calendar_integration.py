"""Add secure iCalendar sources and synchronized event occurrences.

Revision ID: 0004_calendar_integration
Revises: 0003_projects_and_tasks
Create Date: 2026-10-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_calendar_integration"
down_revision: Union[str, None] = "0003_projects_and_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "calendar_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("adapter", sa.String(length=30), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("feed_url_encrypted", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("etag", sa.String(length=500), nullable=True),
        sa.Column("last_modified", sa.String(length=200), nullable=True),
        sa.Column("sync_status", sa.String(length=30), nullable=False),
        sa.Column("last_sync_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column("last_event_count", sa.Integer(), nullable=False),
        sa.Column("last_created_count", sa.Integer(), nullable=False),
        sa.Column("last_updated_count", sa.Integer(), nullable=False),
        sa.Column("last_deleted_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_id",
            "adapter",
            name="uq_calendar_source_owner_adapter",
        ),
    )
    op.create_index(
        op.f("ix_calendar_sources_owner_id"),
        "calendar_sources",
        ["owner_id"],
        unique=False,
    )
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("source_uid", sa.String(length=500), nullable=False),
        sa.Column("occurrence_key", sa.String(length=500), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=1000), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("all_day", sa.Boolean(), nullable=False),
        sa.Column("source_timezone", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["calendar_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "source_uid",
            "occurrence_key",
            name="uq_calendar_event_source_identity",
        ),
    )
    for column in ("owner_id", "source_id", "starts_at", "ends_at"):
        op.create_index(
            op.f(f"ix_calendar_events_{column}"),
            "calendar_events",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in ("owner_id", "source_id", "starts_at", "ends_at"):
        op.drop_index(op.f(f"ix_calendar_events_{column}"), table_name="calendar_events")
    op.drop_table("calendar_events")
    op.drop_index(op.f("ix_calendar_sources_owner_id"), table_name="calendar_sources")
    op.drop_table("calendar_sources")
