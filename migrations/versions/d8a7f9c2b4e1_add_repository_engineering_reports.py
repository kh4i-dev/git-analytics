"""add repository engineering reports

Revision ID: d8a7f9c2b4e1
Revises: c4a8f2d1e9b0
Create Date: 2026-05-21 16:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d8a7f9c2b4e1"
down_revision: str | None = "c4a8f2d1e9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repository_engineering_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("from_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("to_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("staleness_threshold_hours_used", sa.Integer(), nullable=False),
        sa.Column("generated_title", sa.String(length=500), nullable=False),
        sa.Column("custom_title", sa.String(length=500), nullable=True),
        sa.Column("display_repository_name", sa.String(length=500), nullable=True),
        sa.Column("is_repository_anonymized", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("summary_payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("release_notes_markdown", sa.Text(), nullable=False),
        sa.Column("changelog_markdown", sa.Text(), nullable=False),
        sa.Column("risk_insights", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("public_token", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reports_user_generated",
        "repository_engineering_reports",
        ["user_id", "generated_at"],
    )
    op.create_index(
        "ix_reports_repo_range",
        "repository_engineering_reports",
        ["repository_id", "from_date", "to_date"],
    )
    op.create_index(
        "ix_reports_public_token",
        "repository_engineering_reports",
        ["public_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_reports_public_token", table_name="repository_engineering_reports")
    op.drop_index("ix_reports_repo_range", table_name="repository_engineering_reports")
    op.drop_index("ix_reports_user_generated", table_name="repository_engineering_reports")
    op.drop_table("repository_engineering_reports")
