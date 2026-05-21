import pytest
from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.user import User
from app.models.repository import Repository
from app.models.commit import Commit
from app.services.changelog_service import ChangelogService


def test_generate_changelog_empty() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session)
    db = session_factory()

    try:
        # Create a User
        user = User(
            github_id=999,
            github_login="test-user",
            encrypted_github_token="encrypted"
        )
        db.add(user)
        db.commit()

        # Create a repo
        repo = Repository(
            user_id=user.id,
            github_repo_id=123,
            owner="test-owner",
            name="test-repo",
            full_name="test-owner/test-repo",
            is_private=False,
            default_branch="main",
            html_url="https://github.com/test-owner/test-repo"
        )
        db.add(repo)
        db.commit()

        res = ChangelogService.generate_changelog(
            db=db,
            repo_id=repo.id
        )

        assert res["commit_count"] == 0
        assert "Changelog" in res["markdown"]
        assert "[Unreleased]" in res["markdown"]

    finally:
        db.close()
        engine.dispose()


def test_generate_changelog_with_commits() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session)
    db = session_factory()

    try:
        # Create a User
        user = User(
            github_id=999,
            github_login="test-user",
            encrypted_github_token="encrypted"
        )
        db.add(user)
        db.commit()

        # Create a repo
        repo = Repository(
            user_id=user.id,
            github_repo_id=123,
            owner="test-owner",
            name="test-repo",
            full_name="test-owner/test-repo",
            is_private=False,
            default_branch="main",
            html_url="https://github.com/test-owner/test-repo"
        )
        db.add(repo)
        db.commit()

        # Add commits in different weeks/months
        # 1. 2026-05-01 (Friday) - Month: 2026-05, Week: 2026-04-27
        c1 = Commit(
            repository_id=repo.id,
            sha="1111111111111111111111111111111111111111",
            message="feat(core): add core module",
            author_name="Alice",
            author_email="alice@example.com",
            committed_at=datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC),
            html_url="https://github.com/test-owner/test-repo/commit/1111111",
        )
        # 2. 2026-05-20 (Wednesday) - Month: 2026-05, Week: 2026-05-18
        c2 = Commit(
            repository_id=repo.id,
            sha="2222222222222222222222222222222222222222",
            message="fix(ui): improve button active states",
            author_name="Bob",
            author_email="bob@example.com",
            committed_at=datetime(2026, 5, 20, 14, 0, 0, tzinfo=UTC),
            html_url="https://github.com/test-owner/test-repo/commit/2222222",
        )
        db.add_all([c1, c2])
        db.commit()

        # Group by week (default)
        res_week = ChangelogService.generate_changelog(
            db=db,
            repo_id=repo.id,
            group_by="week"
        )
        assert res_week["commit_count"] == 2
        # Should have two week headers
        assert "Tuần 27-04-2026" in res_week["markdown"]
        assert "Tuần 18-05-2026" in res_week["markdown"]
        assert "### Added" in res_week["markdown"]
        assert "### Fixed" in res_week["markdown"]

        # Group by month
        res_month = ChangelogService.generate_changelog(
            db=db,
            repo_id=repo.id,
            group_by="month"
        )
        assert res_month["commit_count"] == 2
        # Should have one month header
        assert "Tháng 05-2026" in res_month["markdown"]

    finally:
        db.close()
        engine.dispose()
