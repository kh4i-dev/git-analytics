import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, RepositoryNotFoundException
from app.db.session import get_db
from app.schemas.response import error_response, success_response
from app.services.analytics_service import AnalyticsService
from app.services.export_service import AnalyticsExportService
from app.utils.auth import require_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


def _get_user_id(request: Request, db) -> int:
    return require_user_id(request, db)


@router.get("/global")
async def global_analytics_overview(
    request: Request,
    branch: str | None = None,
    contributor: str | None = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = _get_user_id(request, db)
    data = AnalyticsService(db).get_global_overview(user_id, branch=branch, contributor=contributor)
    return JSONResponse(success_response(request, data))


@router.get("/export/{format_name}")
async def export_global_analytics(
    request: Request,
    format_name: str,
    branch: str | None = None,
    contributor: str | None = None,
    db: Session = Depends(get_db),
) -> Response:
    from app.models.user import User
    from app.repositories.user_repo import UserRepository
    user_id = _get_user_id(request, db)
    stats = AnalyticsService(db).get_global_overview(user_id, branch=branch, contributor=contributor)
    user = UserRepository(db).get_by_id(user_id)
    username = user.github_login if user else None
    exporter = AnalyticsExportService()
    rows = exporter.build_rows(stats)
    if format_name == "xlsx":
        return Response(
            exporter.to_xlsx(rows),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="git-analytics-kpi-report.xlsx"'},
        )
    if format_name == "pdf":
        return Response(
            exporter.to_pdf(stats, username=username),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="git-analytics-kpi-report.pdf"'},
        )
    return JSONResponse(
        error_response(request, code="UNSUPPORTED_EXPORT_FORMAT", message="Use pdf or xlsx."),
        status_code=400,
    )


@router.get("/{repo_id}/overview")
async def analytics_overview(
    request: Request,
    repo_id: int,
    branch: str | None = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = _get_user_id(request, db)
    data = AnalyticsService(db).get_overview(user_id, repo_id, branch)
    return JSONResponse(success_response(request, data))


@router.get("/{repo_id}/commits")
async def analytics_commits(
    request: Request,
    repo_id: int,
    branch: str | None = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = _get_user_id(request, db)
    data = AnalyticsService(db).get_commits(user_id, repo_id, branch)
    return JSONResponse(success_response(request, data))


@router.get("/{repo_id}/pull-requests")
async def analytics_pull_requests(
    request: Request,
    repo_id: int,
    branch: str | None = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = _get_user_id(request, db)
    data = AnalyticsService(db).get_pull_requests(user_id, repo_id, branch)
    return JSONResponse(success_response(request, data))


@router.get("/{repo_id}/issues")
async def analytics_issues(
    request: Request,
    repo_id: int,
    branch: str | None = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = _get_user_id(request, db)
    data = AnalyticsService(db).get_issues(user_id, repo_id, branch)
    return JSONResponse(success_response(request, data))


@router.get("/{repo_id}/contributors")
async def analytics_contributors(
    request: Request,
    repo_id: int,
    branch: str | None = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = _get_user_id(request, db)
    data = AnalyticsService(db).get_contributors(user_id, repo_id, branch)
    return JSONResponse(success_response(request, data))
