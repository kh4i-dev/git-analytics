import pytest
from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.user import User
from app.models.repository import Repository
from app.models.commit import Commit
from app.services.release_notes_service import ReleaseNotesService


def test_parse_commit_message() -> None:
    # 1. Feature with scope
    parsed = ReleaseNotesService.parse_commit_message("feat(analytics): add branch-aware dashboard filters")
    assert parsed["type"] == "feat"
    assert parsed["scope"] == "analytics"
    assert parsed["description"] == "add branch-aware dashboard filters"
    assert not parsed["is_breaking"]

    # 2. Bug fix without scope
    parsed = ReleaseNotesService.parse_commit_message("fix: resolve crash on refresh")
    assert parsed["type"] == "fix"
    assert parsed["scope"] is None
    assert parsed["description"] == "resolve crash on refresh"
    assert not parsed["is_breaking"]

    # 3. Breaking change with exclamation mark
    parsed = ReleaseNotesService.parse_commit_message("feat(auth)!: remove old session cookie format")
    assert parsed["type"] == "breaking"
    assert parsed["scope"] == "auth"
    assert parsed["description"] == "remove old session cookie format"
    assert parsed["is_breaking"]

    # 4. Breaking change with body keyword
    parsed = ReleaseNotesService.parse_commit_message(
        "refactor: update core database connector\n\nBREAKING CHANGE: change host option name to address."
    )
    assert parsed["type"] == "breaking"
    assert parsed["is_breaking"]

    # 5. Non-conventional commit message
    parsed = ReleaseNotesService.parse_commit_message("some random commit message description")
    assert parsed["type"] == "other"
    assert parsed["scope"] is None
    assert parsed["description"] == "some random commit message description"
    assert not parsed["is_breaking"]


def test_generate_release_notes_empty() -> None:
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

        # Generate notes
        res = ReleaseNotesService.generate_release_notes(
            db=db,
            repo_id=repo.id,
            version_tag="v1.0.0"
        )

        assert res["version"] == "v1.0.0"
        assert res["stats"]["total_commits"] == 0
        assert "Không có thay đổi nào" in res["markdown_output"]
        assert "v1.0.0" in res["markdown_output"]

    finally:
        db.close()
        engine.dispose()


def test_generate_release_notes_with_commits() -> None:
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

        # Add commits
        c1 = Commit(
            repository_id=repo.id,
            sha="1111111111111111111111111111111111111111",
            message="feat(core): initialize analytics tools",
            author_name="Alice",
            author_email="alice@example.com",
            author_login="alice",
            committed_at=datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC),
            branch_name="main",
            html_url="https://github.com/test-owner/test-repo/commit/1111111"
        )
        c2 = Commit(
            repository_id=repo.id,
            sha="2222222222222222222222222222222222222222",
            message="fix(ui): improve responsive tables layout",
            author_name="Bob",
            author_email="bob@example.com",
            author_login="bob",
            committed_at=datetime(2026, 5, 21, 14, 0, 0, tzinfo=UTC),
            branch_name="main",
            html_url="https://github.com/test-owner/test-repo/commit/2222222"
        )
        c3 = Commit(
            repository_id=repo.id,
            sha="3333333333333333333333333333333333333333",
            message="chore: cleanup outdated assets",
            author_name="Alice",
            author_email="alice@example.com",
            author_login="alice",
            committed_at=datetime(2026, 5, 21, 15, 0, 0, tzinfo=UTC),
            branch_name="dev",
            html_url="https://github.com/test-owner/test-repo/commit/3333333"
        )
        db.add_all([c1, c2, c3])
        db.commit()

        # 1. Generate for all branches
        res = ReleaseNotesService.generate_release_notes(
            db=db,
            repo_id=repo.id,
            version_tag="v1.1.0"
        )
        assert res["stats"]["total_commits"] == 3
        assert len(res["groups"]) == 3  # feat, fix, chore
        assert "✨ Tính năng mới" in res["groups"]
        assert "🐛 Sửa lỗi" in res["groups"]
        assert "🔧 Chore" in res["groups"]
        assert "v1.1.0" in res["markdown_output"]

        # 2. Filter by branch "main"
        res_branch = ReleaseNotesService.generate_release_notes(
            db=db,
            repo_id=repo.id,
            branch="main",
            version_tag="v1.1.0"
        )
        assert res_branch["stats"]["total_commits"] == 2
        assert "✨ Tính năng mới" in res_branch["groups"]
        assert "🐛 Sửa lỗi" in res_branch["groups"]
        assert "🔧 Chore" not in res_branch["groups"]

    finally:
        db.close()
        engine.dispose()
