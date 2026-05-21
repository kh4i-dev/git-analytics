"""add ai provider settings

Revision ID: f3a1b2c4d5e6
Revises: d8a7f9c2b4e1
Create Date: 2026-05-22 02:05:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f3a1b2c4d5e6"
down_revision: str | None = "d8a7f9c2b4e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_provider_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("mode IN ('byok', 'cloud')", name="ck_ai_provider_settings_mode"),
        sa.CheckConstraint(
            "provider IN ('openai', 'gemini', 'claude')",
            name="ck_ai_provider_settings_provider",
        ),
        sa.CheckConstraint(
            "((mode = 'byok' AND encrypted_api_key IS NOT NULL) OR "
            "(mode = 'cloud' AND encrypted_api_key IS NULL))",
            name="ck_ai_provider_settings_key_by_mode",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "mode",
            "provider",
            name="uq_ai_provider_settings_user_mode_provider",
        ),
    )
    op.create_index("ix_ai_provider_settings_user_id", "ai_provider_settings", ["user_id"])
    op.create_index(
        "ix_ai_provider_settings_user_default",
        "ai_provider_settings",
        ["user_id", "is_default"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_provider_settings_user_default", table_name="ai_provider_settings")
    op.drop_index("ix_ai_provider_settings_user_id", table_name="ai_provider_settings")
    op.drop_table("ai_provider_settings")
