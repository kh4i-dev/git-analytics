import os
import tempfile
from collections.abc import Generator
from datetime import UTC, datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.config import settings as global_settings
from app.core.security import encrypt_token
from app.core.session import create_session_cookie
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.commit import Commit
from app.models.contributor import Contributor
from app.models.issue import Issue
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.user import User
from app.repositories import RepositoryRepository, UserRepository


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    _, db_path = tempfile.mkstemp(suffix=".db")
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except PermissionError:
            pass


def _make_user(db: Session) -> tuple[User, str]:
    token = encrypt_token("gh-token", encryption_key=global_settings.encryption_key)
    user = UserRepository(db).create({
        "github_id": 3001,
        "github_login": "insightuser",
        "encrypted_github_token": token,
    })
    db.commit()
    return user, create_session_cookie(user.id)


def _make_repo(db: Session, user_id: int) -> Repository:
    repo = RepositoryRepository(db).create({
        "user_id": user_id,
        "github_repo_id": 9901,
        "owner": "insightuser",
        "name": "insights-test",
        "full_name": "insightuser/insights-test",
        "html_url": "https://github.com/insightuser/insights-test",
        "default_branch": "main",
        "last_sync_status": "success",
    })
    db.commit()
    return repo


def _seed_data(db: Session, repo_id: int) -> None:
    contrib = Contributor(
        repo_id=repo_id,
        github_login="insightuser",
        display_name="Insight User",
        source_type="github_user",
    )
    db.add(contrib)
    db.flush()

    db.add(Commit(
        repo_id=repo_id,
        contributor_id=contrib.id,
        sha="def1234567890123456789012345678901234567",
        message="feat(core): add amazing analytics capability",
        author_name="Insight User",
        author_email="insight@example.com",
        author_login="insightuser",
        committed_at=datetime.now(UTC),
        html_url="https://github.com/insightuser/insights-test/commit/def1234",
    ))

    db.add(Commit(
        repo_id=repo_id,
        contributor_id=contrib.id,
        sha="def7890123456789012345678901234567890123",
        message="fix(ui): adjust dashboard layout streaks",
        author_name="Insight User",
        author_email="insight@example.com",
        author_login="insightuser",
        committed_at=datetime.now(UTC),
        html_url="https://github.com/insightuser/insights-test/commit/def7890",
    ))

    db.add(PullRequest(
        repo_id=repo_id,
        contributor_id=contrib.id,
        number=1,
        title="Add analytics feature",
        state="closed",
        is_merged=True,
        author_login="insightuser",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        merged_at=datetime.now(UTC),
        html_url="https://github.com/insightuser/insights-test/pull/1",
    ))

    db.add(Issue(
        repo_id=repo_id,
        contributor_id=contrib.id,
        number=1,
        title="Bug in insights graph",
        state="open",
        author_login="insightuser",
        labels=["bug", "high-priority"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        html_url="https://github.com/insightuser/insights-test/issues/1",
    ))
    db.commit()


def _test_client(db: Session) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: (yield db)
    return TestClient(app)


# ── Auth & Repo Checks ────────────────────────────────────────────────────────

def test_api_insights_requires_auth(db_session: Session) -> None:
    client = _test_client(db_session)
    response = client.get("/api/v1/insights/1")
    assert response.status_code == 401


def test_api_insights_rejects_wrong_repo(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get("/api/v1/insights/9999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REPOSITORY_NOT_FOUND"


# ── Empty Repo Output Verification ────────────────────────────────────────────

def test_api_insights_empty_repo(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/api/v1/insights/{repo.id}")
    assert response.status_code == 200
    data = response.json()["data"]

    # Basic validations
    assert data["activity_score"]["score"] == 0
    assert data["activity_score"]["level"] == "Low"
    assert len(data["heatmap"]) == 365
    assert sum(data["heatmap"].values()) == 0
    assert data["coding_activity"]["current_streak"] == 0
    assert data["coding_activity"]["longest_streak"] == 0
    assert data["commit_intelligence"]["total_commits"] == 0
    assert data["commit_intelligence"]["keywords"]["feat"] == 0
    assert data["pr_intelligence"]["total"] == 0
    assert data["issue_intelligence"]["total"] == 0


# ── Seeded Repo Output Verification ───────────────────────────────────────────

def test_api_insights_with_data(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    _seed_data(db_session, repo.id)

    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/api/v1/insights/{repo.id}")
    assert response.status_code == 200
    data = response.json()["data"]

    # Streaks and score calculations
    assert data["activity_score"]["score"] > 0
    assert data["coding_activity"]["active_days"] == 1
    assert data["coding_activity"]["current_streak"] == 1
    assert data["coding_activity"]["longest_streak"] == 1
    assert data["commit_intelligence"]["total_commits"] == 2
    assert data["commit_intelligence"]["keywords"]["feat"] == 1
    assert data["commit_intelligence"]["keywords"]["fix"] == 1
    assert data["commit_intelligence"]["keywords"]["refactor"] == 0
    assert data["pr_intelligence"]["total"] == 1
    assert data["pr_intelligence"]["success_ratio_pct"] == 100
    assert data["issue_intelligence"]["total"] == 1
    assert data["issue_intelligence"]["bug_count"] == 1


# ── HTML Template Render Verification ─────────────────────────────────────────

def test_dashboard_insights_requires_login(db_session: Session) -> None:
    client = _test_client(db_session)
    response = client.get("/dashboard/1/insights", follow_redirects=False)
    assert response.status_code == 302


def test_dashboard_insights_renders(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/dashboard/{repo.id}/insights")
    assert response.status_code == 200
    assert "insights" in response.text.lower()
    assert "heatmap" in response.text.lower()
    assert "keywordChart" in response.text
