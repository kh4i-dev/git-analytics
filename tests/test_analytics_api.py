import os
import tempfile
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

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


# ── Fixtures ─────────────────────────────────────────────────────────────────

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
        "github_id": 2001,
        "github_login": "testuser",
        "encrypted_github_token": token,
    })
    db.commit()
    return user, create_session_cookie(user.id)


def _make_repo(db: Session, user_id: int) -> Repository:
    repo = RepositoryRepository(db).create({
        "user_id": user_id,
        "github_repo_id": 9001,
        "owner": "testuser",
        "name": "analytics-test",
        "full_name": "testuser/analytics-test",
        "html_url": "https://github.com/testuser/analytics-test",
        "default_branch": "main",
        "last_sync_status": "success",
    })
    db.commit()
    return repo


def _seed_data(db: Session, repo_id: int) -> None:
    contrib = Contributor(
        repo_id=repo_id,
        github_login="testuser",
        display_name="Test User",
        source_type="github_user",
    )
    db.add(contrib)
    db.flush()

    db.add(Commit(
        repo_id=repo_id,
        contributor_id=contrib.id,
        sha="abc1234567890123456789012345678901234567",
        message="feat: add analytics",
        author_name="Test User",
        author_email="test@example.com",
        author_login="testuser",
        committed_at=datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
        html_url="https://github.com/testuser/analytics-test/commit/abc1234",
    ))

    db.add(PullRequest(
        repo_id=repo_id,
        contributor_id=contrib.id,
        number=1,
        title="Add analytics feature",
        state="closed",
        is_merged=True,
        author_login="testuser",
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 2, tzinfo=UTC),
        merged_at=datetime(2026, 5, 2, tzinfo=UTC),
        html_url="https://github.com/testuser/analytics-test/pull/1",
    ))

    db.add(Issue(
        repo_id=repo_id,
        contributor_id=contrib.id,
        number=1,
        title="Bug in analytics",
        state="open",
        author_login="testuser",
        labels=["bug"],
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 1, tzinfo=UTC),
        html_url="https://github.com/testuser/analytics-test/issues/1",
    ))
    db.commit()


def _test_client(db: Session) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: (yield db)
    return TestClient(app)


# ── Auth guard tests ──────────────────────────────────────────────────────────

def test_analytics_overview_requires_auth(db_session: Session) -> None:
    client = _test_client(db_session)
    response = client.get("/api/v1/analytics/1/overview")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_analytics_commits_requires_auth(db_session: Session) -> None:
    client = _test_client(db_session)
    response = client.get("/api/v1/analytics/1/commits")
    assert response.status_code == 401


def test_analytics_pull_requests_requires_auth(db_session: Session) -> None:
    client = _test_client(db_session)
    response = client.get("/api/v1/analytics/1/pull-requests")
    assert response.status_code == 401


def test_analytics_issues_requires_auth(db_session: Session) -> None:
    client = _test_client(db_session)
    response = client.get("/api/v1/analytics/1/issues")
    assert response.status_code == 401


def test_analytics_contributors_requires_auth(db_session: Session) -> None:
    client = _test_client(db_session)
    response = client.get("/api/v1/analytics/1/contributors")
    assert response.status_code == 401


# ── Ownership validation ──────────────────────────────────────────────────────

def test_analytics_rejects_wrong_repo(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    # repo_id=9999 does not belong to this user
    response = client.get("/api/v1/analytics/9999/overview")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REPOSITORY_NOT_FOUND"


def test_analytics_rejects_other_users_repo(db_session: Session) -> None:
    # Create two users each with a repo
    token_a = encrypt_token("tok-a", encryption_key=global_settings.encryption_key)
    user_a = UserRepository(db_session).create({
        "github_id": 3001, "github_login": "user_a",
        "encrypted_github_token": token_a,
    })
    token_b = encrypt_token("tok-b", encryption_key=global_settings.encryption_key)
    user_b = UserRepository(db_session).create({
        "github_id": 3002, "github_login": "user_b",
        "encrypted_github_token": token_b,
    })
    db_session.commit()

    repo_b = RepositoryRepository(db_session).create({
        "user_id": user_b.id,
        "github_repo_id": 8001,
        "owner": "user_b", "name": "secret-repo",
        "full_name": "user_b/secret-repo",
        "html_url": "https://github.com/user_b/secret-repo",
    })
    db_session.commit()

    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, create_session_cookie(user_a.id))

    response = client.get(f"/api/v1/analytics/{repo_b.id}/overview")
    assert response.status_code == 404


# ── Empty repo analytics ──────────────────────────────────────────────────────

def test_analytics_overview_empty_repo(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/api/v1/analytics/{repo.id}/overview")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["total_commits"] == 0
    assert data["summary"]["total_prs"] == 0
    assert data["summary"]["open_issues"] == 0
    assert data["charts"]["commits_per_day"] == []
    assert data["recent"]["commits"] == []


def test_analytics_commits_empty_repo(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/api/v1/analytics/{repo.id}/commits")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["total"] == 0
    assert data["charts"]["per_day"] == []


def test_analytics_prs_empty_repo(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/api/v1/analytics/{repo.id}/pull-requests")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["total"] == 0
    assert data["summary"]["avg_merge_time_hours"] is None


def test_analytics_issues_empty_repo(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/api/v1/analytics/{repo.id}/issues")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["total"] == 0
    assert data["summary"]["avg_close_time_hours"] is None


# ── Seeded data correctness ───────────────────────────────────────────────────

def test_analytics_overview_with_data(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    _seed_data(db_session, repo.id)

    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/api/v1/analytics/{repo.id}/overview")
    assert response.status_code == 200
    data = response.json()["data"]
    s = data["summary"]
    assert s["total_commits"] == 1
    assert s["total_prs"] == 1
    assert s["merged_prs"] == 1
    assert s["open_issues"] == 1
    assert s["total_contributors"] == 1
    assert len(data["recent"]["commits"]) == 1
    assert data["recent"]["commits"][0]["sha"] == "abc1234"


def test_analytics_commits_json_structure(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    _seed_data(db_session, repo.id)

    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/api/v1/analytics/{repo.id}/commits")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert "meta" in body
    data = body["data"]
    assert "summary" in data
    assert "charts" in data
    assert "per_day" in data["charts"]
    assert "by_contributor" in data["charts"]
    assert "recent" in data
    commit = data["recent"][0]
    assert "sha" in commit
    assert "message" in commit
    assert "author_login" in commit
    assert "committed_at" in commit


def test_analytics_prs_json_structure(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    _seed_data(db_session, repo.id)

    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/api/v1/analytics/{repo.id}/pull-requests")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["merged"] == 1
    pr = data["recent"][0]
    assert pr["number"] == 1
    assert pr["is_merged"] is True


def test_analytics_issues_json_structure(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    _seed_data(db_session, repo.id)

    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/api/v1/analytics/{repo.id}/issues")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["open"] == 1
    issue = data["recent"][0]
    assert issue["labels"] == ["bug"]
    assert issue["state"] == "open"


def test_analytics_contributors_json_structure(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    _seed_data(db_session, repo.id)

    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/api/v1/analytics/{repo.id}/contributors")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["total"] >= 1
    top = data["top_contributors"]
    assert isinstance(top, list)
    assert top[0]["count"] >= 1


# ── Dashboard page render tests ───────────────────────────────────────────────

def test_dashboard_overview_requires_login(db_session: Session) -> None:
    client = _test_client(db_session)
    response = client.get("/dashboard/1", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_dashboard_overview_renders(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/dashboard/{repo.id}")
    assert response.status_code == 200
    assert "testuser/analytics-test" in response.text
    assert "Overview" in response.text
    assert "chart.js" in response.text.lower() or "chart.umd" in response.text.lower()


def test_dashboard_commits_renders(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/dashboard/{repo.id}/commits")
    assert response.status_code == 200
    assert "Commits" in response.text


def test_dashboard_prs_renders(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/dashboard/{repo.id}/pull-requests")
    assert response.status_code == 200
    assert "Pull Requests" in response.text


def test_dashboard_issues_renders(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    repo = _make_repo(db_session, user.id)
    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get(f"/dashboard/{repo.id}/issues")
    assert response.status_code == 200
    assert "Issues" in response.text


def test_dashboard_unknown_repo_redirects(db_session: Session) -> None:
    user, cookie = _make_user(db_session)
    client = _test_client(db_session)
    client.cookies.set(global_settings.session_cookie_name, cookie)

    response = client.get("/dashboard/99999", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/repositories"
