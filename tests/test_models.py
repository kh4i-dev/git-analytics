from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import configure_mappers

import app.models  # noqa: F401
from app.db.base import Base


def test_models_create_expected_sqlite_schema() -> None:
    configure_mappers()

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    assert set(inspector.get_table_names()) == {
        "users",
        "branches",
        "repositories",
        "contributors",
        "commits",
        "pull_requests",
        "issues",
        "sync_jobs",
        "repository_engineering_reports",
        "ai_provider_settings",
    }

    unique_constraints = {
        table: {constraint["name"] for constraint in inspector.get_unique_constraints(table)}
        for table in inspector.get_table_names()
    }
    indexes = {
        table: {index["name"] for index in inspector.get_indexes(table)}
        for table in inspector.get_table_names()
    }

    assert "uq_repositories_user_repo" in unique_constraints["repositories"]
    assert "uq_branches_repo_name" in unique_constraints["branches"]
    assert "uq_commits_repo_sha" in unique_constraints["commits"]
    assert "uq_pull_requests_repo_number" in unique_constraints["pull_requests"]
    assert "uq_issues_repo_number" in unique_constraints["issues"]
    assert (
        "uq_ai_provider_settings_user_mode_provider"
        in unique_constraints["ai_provider_settings"]
    )

    assert "ix_repositories_user_id" in indexes["repositories"]
    assert "ix_branches_repository_id" in indexes["branches"]
    assert "ix_branches_repo_default" in indexes["branches"]
    assert "ix_commits_repo_branch" in indexes["commits"]
    assert "ix_commits_repo_date" in indexes["commits"]
    assert "ix_prs_repo_base_branch" in indexes["pull_requests"]
    assert "ix_prs_repo_state" in indexes["pull_requests"]
    assert "ix_issues_repo_state" in indexes["issues"]
    assert "ix_sync_jobs_status" in indexes["sync_jobs"]
    assert "ix_sync_jobs_repository" in indexes["sync_jobs"]
    assert "ix_reports_user_generated" in indexes["repository_engineering_reports"]
    assert "ix_reports_repo_range" in indexes["repository_engineering_reports"]
    assert "ix_reports_public_token" in indexes["repository_engineering_reports"]
    assert "ix_ai_provider_settings_user_id" in indexes["ai_provider_settings"]
    assert "ix_ai_provider_settings_user_default" in indexes["ai_provider_settings"]
