from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.exceptions import RepositoryNotFoundException
from app.db.session import get_db
from app.repositories import RepositoryRepository, SyncJobRepository
from app.schemas.response import success_response
from app.services.sync_queue import sync_queue
from app.utils.auth import require_user_id
from app.utils.timezone import isoformat_vn as _vn_iso

router = APIRouter(prefix="/api/v1/sync", tags=["Sync"])


def _get_user_id(request: Request, db: Session) -> int:
    return require_user_id(request, db)


@router.get("/jobs")
async def list_sync_jobs(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = _get_user_id(request, db)
    jobs = SyncJobRepository(db).list_recent_by_user(user_id, limit=50)
    return JSONResponse(
        success_response(
            request,
            {
                "jobs": [
                    {
                        "id": job.id,
                        "repository_id": job.repository_id,
                        "repository": job.repository.full_name if job.repository else None,
                        "status": job.status,
                        "kind": job.kind,
                        "attempts": job.attempts,
                        "max_attempts": job.max_attempts,
                        "error": job.error,
                        "queued_at": _vn_iso(job.queued_at),
                        "started_at": _vn_iso(job.started_at),
                        "finished_at": _vn_iso(job.finished_at),
                    }
                    for job in jobs
                ],
                "queue": sync_queue.snapshot(),
            },
        )
    )


@router.post("/jobs/{job_id}/retry")
async def retry_sync_job(
    request: Request,
    job_id: int,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = _get_user_id(request, db)
    job_repo = SyncJobRepository(db)
    job = job_repo.get_by_id(job_id)
    if job is None or job.user_id != user_id:
        raise RepositoryNotFoundException("Sync job not found.")

    repo = RepositoryRepository(db).get_by_user_and_id(user_id, job.repository_id)
    if repo is None:
        raise RepositoryNotFoundException("Repository not found.")

    if job.status not in {"failed", "success"}:
        return JSONResponse(
            success_response(
                request,
                {
                    "job_id": job.id,
                    "status": job.status,
                    "message": "Job is already active.",
                    "queue": sync_queue.snapshot(),
                },
            )
        )

    retry_job = job_repo.create_queued(
        user_id=user_id,
        repository_id=job.repository_id,
        kind="retry",
    )
    db.commit()
    sync_queue.enqueue(retry_job.id)
    return JSONResponse(
        success_response(
            request,
            {
                "job_id": retry_job.id,
                "status": retry_job.status,
                "repository_id": retry_job.repository_id,
                "queue": sync_queue.snapshot(),
            },
        )
    )


@router.post("/{repo_id}")
async def enqueue_repository_sync(
    request: Request,
    repo_id: int,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = _get_user_id(request, db)
    repo = RepositoryRepository(db).get_by_user_and_id(user_id, repo_id)
    if repo is None:
        raise RepositoryNotFoundException("Repository not found.")

    job = SyncJobRepository(db).create_queued(
        user_id=user_id,
        repository_id=repo_id,
        kind="manual",
    )
    db.commit()
    sync_queue.enqueue(job.id)
    return JSONResponse(
        success_response(
            request,
            {
                "job_id": job.id,
                "status": job.status,
                "repository_id": repo_id,
                "queue": sync_queue.snapshot(),
            },
        )
    )


@router.post("/{repo_id}/reset")
async def force_reset_sync_api(
    request: Request,
    repo_id: int,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = _get_user_id(request, db)
    repo_repo = RepositoryRepository(db)
    repo = repo_repo.get_by_user_and_id(user_id, repo_id)
    if repo is None:
        raise RepositoryNotFoundException("Repository not found.")

    repo_repo.update_sync_status(
        repo,
        status="failed",
        last_sync_error="Sync was manually force reset.",
        sync_started_at=None,
    )
    db.commit()

    return JSONResponse(
        success_response(
            request,
            {
                "repository_id": repo_id,
                "status": "failed",
                "message": "Sync state successfully force reset to failed.",
            },
        )
    )
