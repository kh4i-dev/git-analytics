"""add multi branch analytics

Revision ID: b6b2f7a0c9d1
Revises: 394f452fcb07
Create Date: 2026-05-21 03:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b6b2f7a0c9d1"
down_revision: str | None = "394f452fcb07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "branches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("github_branch_name", sa.String(length=255), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("last_commit_sha", sa.String(length=40), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "github_branch_name", name="uq_branches_repo_name"),
    )
    op.create_index("ix_branches_repository_id", "branches", ["repository_id"])
    op.create_index("ix_branches_repo_default", "branches", ["repository_id", "is_default"])

    op.add_column(
        "repositories",
        sa.Column(
            "branch_sync_mode",
            sa.String(length=30),
            server_default="default_only",
            nullable=False,
        ),
    )
    op.add_column("repositories", sa.Column("selected_branches", sa.Text(), nullable=True))
    op.add_column("commits", sa.Column("branch_name", sa.String(length=255), nullable=True))
    op.add_column("pull_requests", sa.Column("base_branch", sa.String(length=255), nullable=True))
    op.add_column("pull_requests", sa.Column("head_branch", sa.String(length=255), nullable=True))
    op.create_index("ix_commits_repo_branch", "commits", ["repo_id", "branch_name"])
    op.create_index("ix_prs_repo_base_branch", "pull_requests", ["repo_id", "base_branch"])

    op.execute(
        """
        INSERT INTO branches (repository_id, github_branch_name, is_default, last_commit_sha, synced_at)
        SELECT id, COALESCE(default_branch, 'main'), 1, NULL, last_synced_at
        FROM repositories
        """
    )
    op.execute(
        """
        UPDATE commits
        SET branch_name = (
            SELECT COALESCE(repositories.default_branch, 'main')
            FROM repositories
            WHERE repositories.id = commits.repo_id
        )
        WHERE branch_name IS NULL
        """
    )
    op.execute(
        """
        UPDATE pull_requests
        SET base_branch = (
            SELECT repositories.default_branch
            FROM repositories
            WHERE repositories.id = pull_requests.repo_id
        )
        WHERE base_branch IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_prs_repo_base_branch", table_name="pull_requests")
    op.drop_index("ix_commits_repo_branch", table_name="commits")
    op.drop_column("pull_requests", "head_branch")
    op.drop_column("pull_requests", "base_branch")
    op.drop_column("commits", "branch_name")
    op.drop_column("repositories", "selected_branches")
    op.drop_column("repositories", "branch_sync_mode")
    op.drop_index("ix_branches_repo_default", table_name="branches")
    op.drop_index("ix_branches_repository_id", table_name="branches")
    op.drop_table("branches")
