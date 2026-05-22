import asyncio
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
from app.core.exceptions import AppException
from app.core.security import decrypt_token, encrypt_token
from app.core.session import create_session_cookie
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.repository import Repository
from app.models.user import User
from app.repositories import RepositoryRepository, UserRepository
from app.services.sync_service import SyncResult


def run_async(coro: Any) -> Any:
    return asyncio.run(coro)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    _, db_path = tempfile.mkstemp(suffix=".db")
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session)
    session = session_factory()
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


def create_logged_in_user(db_session: Session) -> tuple[User, str]:
    encrypted_token = encrypt_token(
        "github-token",
        encryption_key=global_settings.encryption_key,
    )
    user = UserRepository(db_session).create(
        {
            "github_id": 1001,
            "github_login": "octo",
            "encrypted_github_token": encrypted_token,
        }
    )
    db_session.commit()
    return user, create_session_cookie(user.id)


class MockGitHubClient:
    def __init__(self, token: str, *, fail: bool = False) -> None:
        self.token = token
        self.fail = fail
        self.closed = False

    async def list_user_repositories(self) -> list[dict[str, Any]]:
        if self.fail:
            raise AppException("GitHub API error.")
        return [
            {
                "id": 101,
                "name": "repo-alpha",
                "full_name": "octo/repo-alpha",
                "owner": {"login": "octo"},
                "private": False,
                "default_branch": "main",
                "html_url": "https://github.com/octo/repo-alpha",
            },
            {
                "id": 102,
                "name": "repo-beta",
                "full_name": "octo/repo-beta",
                "owner": {"login": "octo"},
                "private": True,
                "default_branch": "master",
                "html_url": "https://github.com/octo/repo-beta",
            },
        ]

    async def aclose(self) -> None:
        self.closed = True


def test_import_repositories_saves_repos_to_db(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, session_cookie = create_logged_in_user(db_session)
    app = create_app()

    monkeypatch.setattr(
        "app.routes.repositories.GitHubClient",
        lambda token: MockGitHubClient(token),
    )

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", session_cookie)

    response = client.post("/repositories/import", follow_redirects=False)

    assert response.status_code == 302
    assert "imported=2" in response.headers["location"]

    repos = RepositoryRepository(db_session).list_by_user(user.id, page=1, per_page=100)
    names = {r.name for r in repos}
    assert names == {"repo-alpha", "repo-beta"}


def test_import_repositories_upserts_existing_repos(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, session_cookie = create_logged_in_user(db_session)
    repo_repo = RepositoryRepository(db_session)
    repo_repo.create(
        {
            "user_id": user.id,
            "github_repo_id": 101,
            "owner": "octo",
            "name": "repo-alpha",
            "full_name": "octo/repo-alpha",
            "html_url": "https://github.com/octo/repo-alpha",
            "default_branch": "old-branch",
        }
    )
    db_session.commit()

    app = create_app()

    monkeypatch.setattr(
        "app.routes.repositories.GitHubClient",
        lambda token: MockGitHubClient(token),
    )

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", session_cookie)

    response = client.post("/repositories/import", follow_redirects=False)

    assert response.status_code == 302, f"Expected 302, got {response.status_code}: {response.text[:500]}"
    assert "imported=2" in response.headers["location"]

    repo = repo_repo.get_by_user_github_repo_id(user.id, 101)
    assert repo is not None
    assert repo.default_branch == "main"
    assert repo.name == "repo-alpha"


def test_import_repositories_shows_error_on_github_failure(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session_cookie = create_logged_in_user(db_session)
    app = create_app()

    monkeypatch.setattr(
        "app.routes.repositories.GitHubClient",
        lambda token: MockGitHubClient(token, fail=True),
    )

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", session_cookie)

    response = client.post("/repositories/import", follow_redirects=False)

    assert response.status_code == 302
    assert "error=import_failed" in response.headers["location"]


def test_sync_repository_route_calls_sync_service(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, session_cookie = create_logged_in_user(db_session)
    repo_repo = RepositoryRepository(db_session)
    repo = repo_repo.create(
        {
            "user_id": user.id,
            "github_repo_id": 101,
            "owner": "octo",
            "name": "repo-alpha",
            "full_name": "octo/repo-alpha",
            "html_url": "https://github.com/octo/repo-alpha",
        }
    )
    db_session.commit()

    async def fake_sync_repo(self, *, user_id: int, repo_id: int) -> SyncResult:
        return SyncResult(
            repository_id=repo_id,
            mode="full",
            status="success",
            synced={"commits": 5, "pull_requests": 1, "issues": 2, "contributors": 1},
            started_at=datetime(2026, 5, 21, 12, 0, tzinfo=UTC),
            completed_at=datetime(2026, 5, 21, 12, 1, tzinfo=UTC),
        )

    monkeypatch.setattr(
        "app.routes.repositories.SyncService.sync_repository",
        fake_sync_repo,
    )

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", session_cookie)

    response = client.post(f"/repositories/{repo.id}/sync", follow_redirects=False)

    assert response.status_code == 302
    assert "synced=1" in response.headers["location"]
    assert "mode=full" in response.headers["location"]
    assert "status=success" in response.headers["location"]


def test_sync_repository_route_shows_error_on_failure(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, session_cookie = create_logged_in_user(db_session)
    repo_repo = RepositoryRepository(db_session)
    repo = repo_repo.create(
        {
            "user_id": user.id,
            "github_repo_id": 101,
            "owner": "octo",
            "name": "repo-alpha",
            "full_name": "octo/repo-alpha",
            "html_url": "https://github.com/octo/repo-alpha",
        }
    )
    db_session.commit()

    async def fake_failing_sync(self, *, user_id: int, repo_id: int) -> SyncResult:
        raise AppException("Sync failed because GitHub API returned an error.")

    monkeypatch.setattr(
        "app.routes.repositories.SyncService.sync_repository",
        fake_failing_sync,
    )

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", session_cookie)

    response = client.post(f"/repositories/{repo.id}/sync", follow_redirects=False)

    assert response.status_code == 302
    assert "error=sync_failed" in response.headers["location"]


def test_sync_all_repositories_route_calls_sync_service_for_each_repo(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, session_cookie = create_logged_in_user(db_session)
    repo_repo = RepositoryRepository(db_session)
    repo_ids = []
    for idx in range(2):
        repo = repo_repo.create(
            {
                "user_id": user.id,
                "github_repo_id": 200 + idx,
                "owner": "octo",
                "name": f"repo-{idx}",
                "full_name": f"octo/repo-{idx}",
                "html_url": f"https://github.com/octo/repo-{idx}",
            }
        )
        repo_ids.append(repo.id)
    db_session.commit()

    called: list[int] = []

    async def fake_sync_repo(self, *, user_id: int, repo_id: int) -> SyncResult:
        called.append(repo_id)
        return SyncResult(
            repository_id=repo_id,
            mode="incremental",
            status="success",
            synced={"commits": 1, "pull_requests": 0, "issues": 0, "contributors": 0},
            started_at=datetime(2026, 5, 21, 12, 0, tzinfo=UTC),
            completed_at=datetime(2026, 5, 21, 12, 1, tzinfo=UTC),
        )

    monkeypatch.setattr(
        "app.routes.repositories.SyncService.sync_repository",
        fake_sync_repo,
    )

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", session_cookie)

    response = client.post("/repositories/sync-all", follow_redirects=False)

    assert response.status_code == 302
    assert "synced_all=2" in response.headers["location"]
    assert sorted(called) == sorted(repo_ids)


def test_repositories_page_shows_imported_repos(
    db_session: Session,
) -> None:
    user, session_cookie = create_logged_in_user(db_session)
    repo_repo = RepositoryRepository(db_session)
    repo_repo.create(
        {
            "user_id": user.id,
            "github_repo_id": 101,
            "owner": "octo",
            "name": "repo-alpha",
            "full_name": "octo/repo-alpha",
            "html_url": "https://github.com/octo/repo-alpha",
            "default_branch": "main",
            "last_sync_status": "success",
        }
    )
    db_session.commit()

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", session_cookie)

    response = client.get("/repositories")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
    assert "octo/repo-alpha" in response.text
    assert "Kết Nối GitHub" in response.text
    assert "Sync" in response.text


def test_repositories_page_requires_login(db_session: Session) -> None:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.get("/repositories", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_import_requires_login(db_session: Session) -> None:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.post("/repositories/import", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_sync_requires_login(db_session: Session) -> None:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.post("/repositories/999/sync", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_force_reset_repository_route_marks_failed(
    db_session: Session,
) -> None:
    user, session_cookie = create_logged_in_user(db_session)
    repo_repo = RepositoryRepository(db_session)
    repo = repo_repo.create(
        {
            "user_id": user.id,
            "github_repo_id": 101,
            "owner": "octo",
            "name": "repo-alpha",
            "full_name": "octo/repo-alpha",
            "html_url": "https://github.com/octo/repo-alpha",
            "last_sync_status": "syncing",
            "sync_started_at": datetime(2026, 5, 21, 12, 0, tzinfo=UTC),
        }
    )
    db_session.commit()

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", session_cookie)

    response = client.post(f"/repositories/{repo.id}/reset", follow_redirects=False)

    assert response.status_code == 302
    assert "reset=1" in response.headers["location"]

    updated_repo = repo_repo.get_by_id(repo.id)
    assert updated_repo.last_sync_status == "failed"
    assert updated_repo.last_sync_error == "Sync was manually force reset."
    assert updated_repo.sync_started_at is None


def test_delete_repository_success(
    db_session: Session,
) -> None:
    user, session_cookie = create_logged_in_user(db_session)
    repo_repo = RepositoryRepository(db_session)
    repo = repo_repo.create(
        {
            "user_id": user.id,
            "github_repo_id": 101,
            "owner": "octo",
            "name": "repo-alpha",
            "full_name": "octo/repo-alpha",
            "html_url": "https://github.com/octo/repo-alpha",
        }
    )
    db_session.commit()

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", session_cookie)

    response = client.delete(f"/repositories/{repo.id}")
    assert response.status_code == 200
    assert response.json() == {"success": True}

    assert repo_repo.get_by_id(repo.id) is None


def test_delete_repository_unauthorized_if_wrong_user(
    db_session: Session,
) -> None:
    user, session_cookie = create_logged_in_user(db_session)
    # create another user's repo
    other_user = UserRepository(db_session).create(
        {
            "github_id": 1002,
            "github_login": "other",
            "encrypted_github_token": "token",
        }
    )
    db_session.commit()

    repo_repo = RepositoryRepository(db_session)
    repo = repo_repo.create(
        {
            "user_id": other_user.id,
            "github_repo_id": 102,
            "owner": "other",
            "name": "repo-beta",
            "full_name": "other/repo-beta",
            "html_url": "https://github.com/other/repo-beta",
        }
    )
    db_session.commit()

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", session_cookie)

    response = client.delete(f"/repositories/{repo.id}")
    assert response.status_code == 404

    assert repo_repo.get_by_id(repo.id) is not None


def test_repositories_page_disables_analyze_button_for_unavailable_repo(
    db_session: Session,
) -> None:
    user, session_cookie = create_logged_in_user(db_session)
    repo_repo = RepositoryRepository(db_session)
    repo_repo.create(
        {
            "user_id": user.id,
            "github_repo_id": 101,
            "owner": "octo",
            "name": "repo-alpha",
            "full_name": "octo/repo-alpha",
            "html_url": "https://github.com/octo/repo-alpha",
            "last_sync_status": "failed",
            "last_sync_error": "Repository not found or access removed",
        }
    )
    db_session.commit()

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", session_cookie)

    response = client.get("/repositories")
    assert response.status_code == 200

    html = response.text
    assert "Mất quyền truy cập" in html
    assert "disabled" in html
    assert "Không thể phân tích repository này" in html

