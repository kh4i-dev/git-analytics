import asyncio
import contextlib
import logging
from datetime import timedelta

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.repository import Repository
from app.repositories import SyncJobRepository
from app.services.sync_service import SyncService

from app.utils.timezone import is_stale_sync, now_utc

logger = logging.getLogger(__name__)


class SyncQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._periodic_task: asyncio.Task[None] | None = None
        self._known_ids: set[int] = set()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._worker(), name="git-analytics-sync-worker")
        asyncio.create_task(self._recover_queued_jobs(), name="git-analytics-sync-recovery")
        if self._periodic_task is None or self._periodic_task.done():
            self._periodic_task = asyncio.create_task(
                self._periodic_enqueue(),
                name="git-analytics-auto-sync",
            )

    async def stop(self) -> None:
        tasks = [task for task in [self._task, self._periodic_task] if task is not None]
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task

    def enqueue(self, job_id: int) -> None:
        if job_id in self._known_ids:
            return
        self._known_ids.add(job_id)
        self._queue.put_nowait(job_id)

    def snapshot(self) -> dict[str, int]:
        return {"queued": self._queue.qsize(), "known": len(self._known_ids)}

    async def _worker(self) -> None:
        while True:
            job_id = await self._queue.get()
            self._known_ids.discard(job_id)
            try:
                await self._run_job(job_id)
            except Exception:
                logger.exception("Sync job worker failed for job_id=%s", job_id)
            finally:
                self._queue.task_done()

    async def _periodic_enqueue(self) -> None:
        interval = max(5, settings.auto_sync_interval_minutes) * 60
        while True:
            await asyncio.sleep(interval)
            db = SessionLocal()
            try:
                job_repo = SyncJobRepository(db)
                stale_before = now_utc() - timedelta(minutes=30)
                for job in job_repo.list_stale_running(stale_before):
                    logger.warning("Sync job %s exceeded 30 minutes. Marking failed.", job.id)
                    job_repo.mark_failed(job, "Sync job timed out and was marked stale.")
                db.commit()

                # 1. Detect stale sync:
                # If status = syncing and sync_started_at > 30 minutes, auto mark failed/stale.
                for repo in db.scalars(select(Repository).where(Repository.last_sync_status == "syncing")).all():
                    if is_stale_sync(repo.sync_started_at, threshold_minutes=30):
                        logger.warning(
                            "Repo %s: Sync has been running since %s (exceeded 30 minutes). Marking as stale/failed.",
                            repo.id,
                            repo.sync_started_at
                        )
                        repo.last_sync_status = "failed"
                        repo.last_sync_error = "Sync timed out (stale sync)"
                        repo.sync_started_at = None
                        db.commit()

                # 2. Auto-enqueue jobs
                for user_repo in db.scalars(select(Repository)).all():
                    if user_repo.last_sync_status == "syncing":
                        continue
                    job = job_repo.create_queued(
                        user_id=user_repo.user_id,
                        repository_id=user_repo.id,
                        kind="auto",
                    )
                    db.commit()
                    self.enqueue(job.id)
            except Exception:
                db.rollback()
                logger.exception("Auto sync enqueue failed")
            finally:
                db.close()

    async def _recover_queued_jobs(self) -> None:
        db = SessionLocal()
        try:
            job_repo = SyncJobRepository(db)
            stale_before = now_utc() - timedelta(minutes=30)
            recovered = 0
            for job in job_repo.list_stale_running(stale_before):
                job_repo.mark_retry_queued(job, "Recovered stale running job after worker restart.")
                recovered += 1
            for job in job_repo.list_queued(limit=100):
                self.enqueue(job.id)
                recovered += 1
            db.commit()
            if recovered:
                logger.info("Recovered %s sync job(s) into the worker queue", recovered)
        except Exception:
            db.rollback()
            logger.exception("Sync job recovery failed")
        finally:
            db.close()

    async def _run_job(self, job_id: int) -> None:
        db = SessionLocal()
        try:
            job_repo = SyncJobRepository(db)
            job = job_repo.get_by_id(job_id)
            if job is None or job.status not in {"queued", "running"}:
                return
            job_repo.mark_running(job)
            db.commit()

            try:
                await SyncService(db).sync_repository(
                    user_id=job.user_id,
                    repo_id=job.repository_id,
                )
                job_repo.mark_success(job)
                db.commit()
            except Exception as exc:
                db.rollback()
                job = job_repo.get_by_id(job_id)
                if job is None:
                    return
                error = str(exc) or exc.__class__.__name__
                if job.attempts < job.max_attempts:
                    job_repo.mark_retry_queued(job, error)
                    db.commit()
                    self.enqueue(job.id)
                    return
                job_repo.mark_failed(job, error)
                db.commit()
        finally:
            db.close()


sync_queue = SyncQueue()
