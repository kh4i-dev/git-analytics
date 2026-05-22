from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.exceptions import DatabaseIntegrityException, ValidationException
from app.db.base import Base
from app.repositories import (
    CommitRepository,
    ContributorRepository,
    IssueRepository,
    PullRequestRepository,
    RepositoryRepository,
    UserRepository,
)


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


def create_user_and_repo(session: Session) -> tuple[int, int]:
    user = UserRepository(session).create(
        {
            "github_id": 123,
            "github_login": "demo",
            "encrypted_github_token": "encrypted",
        }
    )
    repository = RepositoryRepository(session).create(
        {
            "user_id": user.id,
            "github_repo_id": 456,
            "owner": "demo",
            "name": "repo",
            "full_name": "demo/repo",
            "html_url": "https://github.com/demo/repo",
        }
    )
    return user.id, repository.id


def test_commit_upsert_updates_existing_row_and_analytics(db_session: Session) -> None:
    _, repo_id = create_user_and_repo(db_session)
    contributor = ContributorRepository(db_session).create(
        {
            "repo_id": repo_id,
            "github_login": "demo",
            "display_name": "Demo User",
            "source_type": "github_user",
        }
    )
    now = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
    commit_repo = CommitRepository(db_session)

    inserted = commit_repo.upsert_many(
        [
            {
                "repo_id": repo_id,
                "contributor_id": contributor.id,
                "sha": "abc123",
                "message": "initial",
                "author_name": "Demo User",
                "author_email": "demo@example.com",
                "author_login": "demo",
                "committed_at": now,
                "html_url": "https://github.com/demo/repo/commit/abc123",
            },
            {
                "repo_id": repo_id,
                "contributor_id": contributor.id,
                "sha": "def456",
                "message": "second",
                "author_name": "Demo User",
                "author_email": "demo@example.com",
                "author_login": "demo",
                "committed_at": now + timedelta(days=1),
                "html_url": "https://github.com/demo/repo/commit/def456",
            },
        ]
    )
    updated = commit_repo.upsert_many(
        [
            {
                "repo_id": repo_id,
                "contributor_id": contributor.id,
                "sha": "abc123",
                "message": "updated",
                "author_name": "Demo User",
                "author_email": "demo@example.com",
                "author_login": "demo",
                "committed_at": now,
                "html_url": "https://github.com/demo/repo/commit/abc123",
            }
        ]
    )

    commit = commit_repo.get_by_repo_sha(repo_id, "abc123")
    assert inserted == 2
    assert updated == 1
    assert commit is not None
    assert commit.message == "updated"
    assert len(commit_repo.list_by_repo(repo_id, page=1, per_page=1)) == 1
    assert commit_repo.commits_per_day(repo_id) == [
        {"date": "2026-05-20", "count": 1},
        {"date": "2026-05-21", "count": 1},
    ]
    assert commit_repo.commits_by_contributor(repo_id)[0]["count"] == 2


def test_commit_upsert_merges_same_sha_seen_on_multiple_branches(
    db_session: Session,
) -> None:
    _, repo_id = create_user_and_repo(db_session)
    now = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
    commit_repo = CommitRepository(db_session)
    row = {
        "repo_id": repo_id,
        "sha": "abc123",
        "message": "shared commit",
        "author_name": "Demo User",
        "author_email": "demo@example.com",
        "author_login": "demo",
        "committed_at": now,
        "html_url": "https://github.com/demo/repo/commit/abc123",
    }

    count = commit_repo.upsert_many(
        [
            {**row, "branch_name": "main"},
            {**row, "branch_name": "release"},
        ]
    )

    commits = commit_repo.list_by_repo(repo_id)
    assert count == 1
    assert len(commits) == 1
    assert commits[0].branch_name == "main,release"


def test_pull_request_and_issue_upserts_and_summaries(db_session: Session) -> None:
    _, repo_id = create_user_and_repo(db_session)
    now = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)

    pr_repo = PullRequestRepository(db_session)
    pr_repo.upsert_many(
        [
            {
                "repo_id": repo_id,
                "number": 1,
                "title": "Open PR",
                "state": "open",
                "is_merged": False,
                "author_login": "demo",
                "created_at": now,
                "updated_at": now,
                "html_url": "https://github.com/demo/repo/pull/1",
            },
            {
                "repo_id": repo_id,
                "number": 2,
                "title": "Merged PR",
                "state": "closed",
                "is_merged": True,
                "author_login": "demo",
                "created_at": now,
                "updated_at": now,
                "merged_at": now + timedelta(hours=1),
                "html_url": "https://github.com/demo/repo/pull/2",
            },
        ]
    )

    issue_repo = IssueRepository(db_session)
    issue_repo.upsert_many(
        [
            {
                "repo_id": repo_id,
                "number": 1,
                "title": "Open issue",
                "state": "open",
                "author_login": "demo",
                "labels": ["bug"],
                "created_at": now,
                "updated_at": now,
                "html_url": "https://github.com/demo/repo/issues/1",
            },
            {
                "repo_id": repo_id,
                "number": 2,
                "title": "Closed issue",
                "state": "closed",
                "author_login": "demo",
                "labels": [],
                "created_at": now,
                "updated_at": now,
                "closed_at": now + timedelta(hours=2),
                "html_url": "https://github.com/demo/repo/issues/2",
            },
        ]
    )

    assert pr_repo.pr_status_summary(repo_id) == {"open": 1, "closed": 0, "merged": 1}
    assert issue_repo.issues_by_state(repo_id) == {"closed": 1, "open": 1}


def test_repository_layer_wraps_db_integrity_errors(db_session: Session) -> None:
    user_repo = UserRepository(db_session)
    user_repo.create(
        {
            "github_id": 123,
            "github_login": "demo",
            "encrypted_github_token": "encrypted",
        }
    )

    with pytest.raises(DatabaseIntegrityException):
        user_repo.create(
            {
                "github_id": 123,
                "github_login": "demo2",
                "encrypted_github_token": "encrypted",
            }
        )


def test_pagination_validation(db_session: Session) -> None:
    _, repo_id = create_user_and_repo(db_session)

    with pytest.raises(ValidationException):
        CommitRepository(db_session).list_by_repo(repo_id, page=0)
