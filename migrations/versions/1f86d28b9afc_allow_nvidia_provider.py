"""allow_nvidia_provider

Revision ID: 1f86d28b9afc
Revises: a6c4d9e8f1b2
Create Date: 2026-05-22 12:39:51.163286
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '1f86d28b9afc'
down_revision: str | None = 'a6c4d9e8f1b2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("ai_provider_settings") as batch_op:
        batch_op.drop_constraint("ck_ai_provider_settings_provider", type_="check")
        batch_op.create_check_constraint(
            "ck_ai_provider_settings_provider",
            "provider IN ('openai', 'gemini', 'claude', 'nvidia')"
        )


def downgrade() -> None:
    with op.batch_alter_table("ai_provider_settings") as batch_op:
        batch_op.drop_constraint("ck_ai_provider_settings_provider", type_="check")
        batch_op.create_check_constraint(
            "ck_ai_provider_settings_provider",
            "provider IN ('openai', 'gemini', 'claude')"
        )
