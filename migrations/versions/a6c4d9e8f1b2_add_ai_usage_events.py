"""add ai usage events

Revision ID: a6c4d9e8f1b2
Revises: f3a1b2c4d5e6
Create Date: 2026-05-22 03:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a6c4d9e8f1b2"
down_revision: str | None = "f3a1b2c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("operation", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("usage_units", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_usage_events_user_created",
        "ai_usage_events",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_ai_usage_events_provider_created",
        "ai_usage_events",
        ["provider", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_usage_events_provider_created", table_name="ai_usage_events")
    op.drop_index("ix_ai_usage_events_user_created", table_name="ai_usage_events")
    op.drop_table("ai_usage_events")
