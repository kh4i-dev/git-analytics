from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationException, RepositoryNotFoundException
from app.utils.timezone import isoformat_vn as _vn_iso
from app.core.session import parse_session_cookie
from app.db.session import get_db
from app.repositories import RepositoryRepository, SyncJobRepository, UserRepository
from app.schemas.response import success_response
from app.services.sync_queue import sync_queue

router = APIRouter(prefix="/api/v1/sync", tags=["Sync"])


def _get_user_id(request: Request, db: Session) -> int:
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        raise AuthenticationException("Authentication required.")
    user_id = parse_session_cookie(cookie)
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise AuthenticationException("User not found.")
    return user_id


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


@router.get("/jobs")
async def list_sync_jobs(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    _get_user_id(request, db)
    jobs = SyncJobRepository(db).list_recent(limit=50)
    return JSONResponse(
        success_response(
            request,
            {
                "jobs": [
                    {
                        "id": job.id,
                        "repository_id": job.repository_id,
                        "status": job.status,
                        "kind": job.kind,
                        "attempts": job.attempts,
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
