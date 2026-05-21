import asyncio
import contextlib
import logging

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.repository import Repository
from app.repositories import SyncJobRepository
from app.services.sync_service import SyncService

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
                job_repo.mark_failed(job, str(exc) or exc.__class__.__name__)
                db.commit()
        finally:
            db.close()


sync_queue = SyncQueue()
