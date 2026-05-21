from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.sync_job import SyncJob
from app.repositories.base import BaseRepository


class SyncJobRepository(BaseRepository[SyncJob]):
    def get_by_id(self, job_id: int) -> SyncJob | None:
        try:
            return self.db.get(SyncJob, job_id)
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_active_for_repo(self, repository_id: int) -> SyncJob | None:
        try:
            return self.db.scalar(
                select(SyncJob)
                .where(
                    SyncJob.repository_id == repository_id,
                    SyncJob.status.in_(["queued", "running"]),
                )
                .order_by(SyncJob.queued_at.desc())
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def list_recent(self, limit: int = 50) -> Sequence[SyncJob]:
        try:
            return self.db.scalars(
                select(SyncJob)
                .order_by(SyncJob.queued_at.desc(), SyncJob.id.desc())
                .limit(limit)
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def list_recent_by_user(self, user_id: int, limit: int = 50) -> Sequence[SyncJob]:
        try:
            return self.db.scalars(
                select(SyncJob)
                .where(SyncJob.user_id == user_id)
                .order_by(SyncJob.queued_at.desc(), SyncJob.id.desc())
                .limit(limit)
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def list_queued(self, limit: int = 100) -> Sequence[SyncJob]:
        try:
            return self.db.scalars(
                select(SyncJob)
                .where(SyncJob.status == "queued")
                .order_by(SyncJob.queued_at.asc(), SyncJob.id.asc())
                .limit(limit)
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def list_stale_running(self, older_than: datetime) -> Sequence[SyncJob]:
        try:
            return self.db.scalars(
                select(SyncJob).where(
                    SyncJob.status == "running",
                    SyncJob.started_at.is_not(None),
                    SyncJob.started_at < older_than,
                )
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def create_queued(self, *, user_id: int, repository_id: int, kind: str = "manual") -> SyncJob:
        existing = self.get_active_for_repo(repository_id)
        if existing is not None:
            return existing
        job = SyncJob(user_id=user_id, repository_id=repository_id, kind=kind, status="queued")
        self.db.add(job)
        self._flush()
        return job

    def mark_running(self, job: SyncJob) -> SyncJob:
        job.status = "running"
        job.attempts += 1
        job.started_at = datetime.now(UTC)
        job.error = None
        self._flush()
        return job

    def mark_success(self, job: SyncJob) -> SyncJob:
        job.status = "success"
        job.finished_at = datetime.now(UTC)
        job.error = None
        self._flush()
        return job

    def mark_failed(self, job: SyncJob, error: str) -> SyncJob:
        job.status = "failed"
        job.finished_at = datetime.now(UTC)
        job.error = error[:500]
        self._flush()
        return job

    def mark_retry_queued(self, job: SyncJob, error: str) -> SyncJob:
        job.status = "queued"
        job.finished_at = None
        job.started_at = None
        job.error = error[:500]
        self._flush()
        return job
