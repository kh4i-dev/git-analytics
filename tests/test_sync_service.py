import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.exceptions import GitHubAPIError, GitHubRateLimitExceeded, SyncFailedException, GitHubNotFound
from app.core.security import decrypt_token, encrypt_token, generate_encryption_key
from app.db.base import Base
from app.models.commit import Commit
from app.models.contributor import Contributor
from app.models.issue import Issue
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.branch import Branch
from app.repositories import RepositoryRepository, UserRepository
from app.services.sync_service import SyncService


def run_async(coro: Any) -> Any:
    return asyncio.run(coro)


class FakeGitHubClient:
    def __init__(
        self,
        *,
        rate_limit_remaining: int = 5000,
        fail_on: str | None = None,
    ) -> None:
        self.rate_limit_remaining = rate_limit_remaining
        self.fail_on = fail_on
        self.closed = False
        self.calls: list[tuple[str, Any]] = []

    async def get_rate_limit(self) -> dict[str, Any]:
        self.calls.append(("get_rate_limit", None))
        return {"limit": 5000, "remaining": self.rate_limit_remaining, "reset_at": None}

    async def list_contributors(self, owner: str, repo: str) -> list[dict[str, Any]]:
        self.calls.append(("list_contributors", (owner, repo)))
        return [{"login": "octo", "avatar_url": "https://avatars.test/octo.png"}]

    async def list_commits(
        self,
        owner: str,
        repo: str,
        since: datetime | str | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(("list_commits", since))
        if self.fail_on == "commits":
            raise GitHubAPIError("Commit fetch failed.")
        if self.fail_on == "not_found":
            raise GitHubNotFound("Not Found")
        if self.fail_on == "bad_commit_payload":
            return [
                {
                    "sha": "bad123",
                    "commit": {
                        "message": "bad",
                        "author": {
                            "name": "Octo",
                            "email": "octo@example.com",
                            "date": "2026-05-20T10:00:00Z",
                        },
                    },
                    "author": {"login": "octo"},
                }
            ]
        return [
            {
                "sha": "abc123",
                "commit": {
                    "message": "initial commit",
                    "author": {
                        "name": "Octo",
                        "email": "octo@example.com",
                        "date": "2026-05-20T10:00:00Z",
                    },
                    "committer": {
                        "name": "Octo",
                        "email": "octo@example.com",
                        "date": "2026-05-20T10:01:00Z",
                    },
                },
                "author": {
                    "login": "octo",
                    "avatar_url": "https://avatars.test/octo.png",
                },
                "committer": {"login": "octo"},
                "html_url": "https://github.com/octo/repo/commit/abc123",
            }
        ]

    async def list_branches(self, owner: str, repo: str) -> list[dict[str, Any]]:
        self.calls.append(("list_branches", (owner, repo)))
        return [{"name": "main", "commit": {"sha": "abc123"}}]

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "all",
        since: datetime | str | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(("list_pull_requests", (state, since)))
        return [
            {
                "number": 7,
                "title": "Add feature",
                "state": "closed",
                "merged_at": "2026-05-20T12:00:00Z",
                "user": {
                    "login": "octo",
                    "avatar_url": "https://avatars.test/octo.png",
                },
                "draft": False,
                "created_at": "2026-05-20T11:00:00Z",
                "updated_at": "2026-05-20T12:00:00Z",
                "closed_at": "2026-05-20T12:00:00Z",
                "html_url": "https://github.com/octo/repo/pull/7",
            }
        ]

    async def list_issues(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "all",
        since: datetime | str | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(("list_issues", (state, since)))
        return [
            {
                "number": 3,
                "title": "Bug",
                "state": "open",
                "user": {
                    "login": "octo",
                    "avatar_url": "https://avatars.test/octo.png",
                },
                "labels": [{"name": "bug", "color": "d73a4a"}],
                "created_at": "2026-05-20T09:00:00Z",
                "updated_at": "2026-05-20T09:00:00Z",
                "closed_at": None,
                "html_url": "https://github.com/octo/repo/issues/3",
            },
            {
                "number": 7,
                "title": "PR mirrored as issue",
                "state": "closed",
                "user": {"login": "octo"},
                "labels": [],
                "pull_request": {"url": "https://api.github.test/pulls/7"},
                "created_at": "2026-05-20T11:00:00Z",
                "updated_at": "2026-05-20T12:00:00Z",
                "html_url": "https://github.com/octo/repo/pull/7",
            },
        ]

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def create_user_and_repo(
    session: Session,
    *,
    encrypted_token: str = "encrypted-token",
    last_synced_at: datetime | None = None,
) -> tuple[int, int]:
    user = UserRepository(session).create(
        {
            "github_id": 123,
            "github_login": "octo",
            "encrypted_github_token": encrypted_token,
        }
    )
    repository = RepositoryRepository(session).create(
        {
            "user_id": user.id,
            "github_repo_id": 456,
            "owner": "octo",
            "name": "repo",
            "full_name": "octo/repo",
            "html_url": "https://github.com/octo/repo",
            "last_synced_at": last_synced_at,
        }
    )
    session.commit()
    return user.id, repository.id


def test_sync_repository_full_sync_persists_github_data(db_session: Session) -> None:
    user_id, repo_id = create_user_and_repo(db_session)
    fake_client = FakeGitHubClient()
    seen_tokens: list[str] = []

    service = SyncService(
        db_session,
        github_client_factory=lambda token: seen_tokens.append(token) or fake_client,
        token_decrypter=lambda encrypted: f"decrypted:{encrypted}",
    )

    result = run_async(service.sync_repository(user_id=user_id, repo_id=repo_id))

    repository = db_session.get(Repository, repo_id)
    commit = db_session.scalar(select(Commit).where(Commit.repo_id == repo_id))
    pull_request = db_session.scalar(
        select(PullRequest).where(PullRequest.repo_id == repo_id)
    )
    issue = db_session.scalar(select(Issue).where(Issue.repo_id == repo_id))
    contributors = db_session.scalars(
        select(Contributor).where(Contributor.repo_id == repo_id)
    ).all()
    branch = db_session.scalar(select(Branch).where(Branch.repository_id == repo_id))

    assert result.mode == "full"
    assert result.synced == {
        "contributors": 1,
        "branches": 1,
        "commits": 1,
        "pull_requests": 1,
        "issues": 1,
    }
    assert repository is not None
    assert repository.last_sync_status == "success"
    assert repository.last_sync_error is None
    assert repository.last_synced_at is not None
    assert commit is not None
    assert commit.sha == "abc123"
    assert commit.branch_name == "main"
    assert branch is not None
    assert branch.github_branch_name == "main"
    assert branch.last_commit_sha == "abc123"
    assert branch.synced_at is not None
    assert pull_request is not None
    assert pull_request.is_merged is True
    assert issue is not None
    assert issue.labels == ["bug"]
    assert len(contributors) == 1
    assert seen_tokens == ["decrypted:encrypted-token"]
    assert fake_client.closed is True


def test_sync_repository_incremental_passes_since(db_session: Session) -> None:
    last_synced_at = datetime(2026, 5, 19, 8, 0, tzinfo=UTC)
    user_id, repo_id = create_user_and_repo(
        db_session,
        last_synced_at=last_synced_at,
    )
    fake_client = FakeGitHubClient()
    service = SyncService(
        db_session,
        github_client_factory=lambda _token: fake_client,
        token_decrypter=lambda _encrypted: "token",
    )

    result = run_async(service.sync_repository(user_id=user_id, repo_id=repo_id))

    assert result.mode == "incremental"
    assert ("list_commits", last_synced_at) in fake_client.calls
    assert ("list_pull_requests", ("all", last_synced_at)) in fake_client.calls
    assert ("list_issues", ("all", last_synced_at)) in fake_client.calls


def test_sync_repository_failure_rolls_back_and_marks_failed(
    db_session: Session,
) -> None:
    user_id, repo_id = create_user_and_repo(db_session)
    fake_client = FakeGitHubClient(fail_on="commits")
    service = SyncService(
        db_session,
        github_client_factory=lambda _token: fake_client,
        token_decrypter=lambda _encrypted: "token",
    )

    with pytest.raises(GitHubAPIError):
        run_async(service.sync_repository(user_id=user_id, repo_id=repo_id))

    repository = db_session.get(Repository, repo_id)
    assert repository is not None
    assert repository.last_sync_status == "failed"
    assert repository.last_sync_error == "Commit fetch failed."
    assert repository.last_synced_at is None
    assert db_session.scalars(select(Commit).where(Commit.repo_id == repo_id)).all() == []
    assert fake_client.closed is True


def test_sync_repository_handles_github_not_found(
    db_session: Session,
) -> None:
    user_id, repo_id = create_user_and_repo(db_session)
    fake_client = FakeGitHubClient(fail_on="not_found")
    service = SyncService(
        db_session,
        github_client_factory=lambda _token: fake_client,
        token_decrypter=lambda _encrypted: "token",
    )

    with pytest.raises(SyncFailedException) as excinfo:
        run_async(service.sync_repository(user_id=user_id, repo_id=repo_id))

    assert "Repository not found or access removed" in str(excinfo.value)

    repository = db_session.get(Repository, repo_id)
    assert repository is not None
    assert repository.last_sync_status == "failed"
    assert repository.last_sync_error == "Repository not found or access removed"
    assert repository.last_synced_at is None
    assert fake_client.closed is True


def test_sync_repository_rolls_back_partial_db_writes(db_session: Session) -> None:
    user_id, repo_id = create_user_and_repo(db_session)
    fake_client = FakeGitHubClient(fail_on="bad_commit_payload")
    service = SyncService(
        db_session,
        github_client_factory=lambda _token: fake_client,
        token_decrypter=lambda _encrypted: "token",
    )

    with pytest.raises(SyncFailedException):
        run_async(service.sync_repository(user_id=user_id, repo_id=repo_id))

    repository = db_session.get(Repository, repo_id)
    assert repository is not None
    assert repository.last_sync_status == "failed"
    assert repository.last_synced_at is None
    assert (
        db_session.scalars(select(Contributor).where(Contributor.repo_id == repo_id)).all()
        == []
    )


def test_sync_repository_low_rate_limit_marks_failed(db_session: Session) -> None:
    user_id, repo_id = create_user_and_repo(db_session)
    fake_client = FakeGitHubClient(rate_limit_remaining=1)
    service = SyncService(
        db_session,
        github_client_factory=lambda _token: fake_client,
        token_decrypter=lambda _encrypted: "token",
    )

    with pytest.raises(GitHubRateLimitExceeded):
        run_async(service.sync_repository(user_id=user_id, repo_id=repo_id))

    repository = db_session.get(Repository, repo_id)
    assert repository is not None
    assert repository.last_sync_status == "failed"
    assert "rate limit" in (repository.last_sync_error or "").lower()
    assert repository.last_synced_at is None


def test_security_encrypt_decrypt_roundtrip() -> None:
    encryption_key = generate_encryption_key()
    encrypted = encrypt_token("github-token", encryption_key=encryption_key)

    assert encrypted != "github-token"
    assert decrypt_token(encrypted, encryption_key=encryption_key) == "github-token"
