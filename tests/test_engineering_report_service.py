from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.commit import Commit
from app.models.repository import Repository
from app.models.user import User
from app.repositories.engineering_report_repository import EngineeringReportRepository
from app.services.engineering_report_service import EngineeringReportService


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, class_=Session)()


def _seed_repo(db: Session) -> Repository:
    user = User(github_id=1, github_login="alice", encrypted_github_token="token")
    db.add(user)
    db.commit()
    repo = Repository(
        user_id=user.id,
        github_repo_id=10,
        owner="alice",
        name="demo",
        full_name="alice/demo",
        html_url="https://github.com/alice/demo",
        last_synced_at=datetime.now(UTC),
    )
    db.add(repo)
    db.commit()
    commit = Commit(
        repo_id=repo.id,
        sha="a" * 40,
        message="feat(report): add snapshot export",
        author_name="Alice",
        author_email="alice@example.com",
        author_login="alice",
        committed_at=datetime.now(UTC) - timedelta(days=1),
        html_url="https://github.com/alice/demo/commit/" + "a" * 40,
    )
    db.add(commit)
    db.commit()
    return repo


def test_create_report_stores_snapshot_and_range() -> None:
    db = _db()
    try:
        repo = _seed_repo(db)
        report = EngineeringReportService.create_report(
            db,
            user_id=repo.user_id,
            repository_id=repo.id,
            from_date=(datetime.now(UTC) - timedelta(days=2)).isoformat(),
            to_date=datetime.now(UTC).isoformat(),
            custom_title="Client update",
        )
        db.commit()

        assert report.custom_title == "Client update"
        assert report.generated_title.startswith("alice/demo")
        assert report.from_date < report.to_date
        assert report.summary_payload["counts"]["commits"] == 1
        assert "feat(report)" not in report.release_notes_markdown
        assert "snapshot export" in report.release_notes_markdown
    finally:
        db.close()


def test_publish_revoke_and_republish_rotates_public_token() -> None:
    db = _db()
    try:
        repo = _seed_repo(db)
        report = EngineeringReportService.create_report(db, user_id=repo.user_id, repository_id=repo.id)
        db.commit()

        published = EngineeringReportService.publish_report(db, user_id=repo.user_id, report_id=report.id)
        first_token = published.public_token
        assert first_token

        revoked = EngineeringReportService.revoke_report(db, user_id=repo.user_id, report_id=report.id)
        assert revoked.public_token is None
        assert revoked.revoked_at is not None
        assert EngineeringReportRepository(db).get_by_public_token(first_token) is None

        republished = EngineeringReportService.publish_report(db, user_id=repo.user_id, report_id=report.id)
        assert republished.public_token
        assert republished.public_token != first_token
    finally:
        db.close()


def test_public_serialization_uses_report_level_anonymization() -> None:
    db = _db()
    try:
        repo = _seed_repo(db)
        report = EngineeringReportService.create_report(db, user_id=repo.user_id, repository_id=repo.id)
        report = EngineeringReportService.publish_report(
            db,
            user_id=repo.user_id,
            report_id=report.id,
            is_repository_anonymized=True,
            display_repository_name="Client Project",
        )

        public_data = EngineeringReportService.serialize(report, include_private=False)
        owner_data = EngineeringReportService.serialize(report, include_private=True)

        assert public_data["repository_full_name"] == "Client Project"
        assert public_data["public_repository_name"] == "Client Project"
        assert owner_data["repository_full_name"] == "alice/demo"
    finally:
        db.close()
