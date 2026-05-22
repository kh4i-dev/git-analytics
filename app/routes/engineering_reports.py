from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories import EngineeringReportRepository, RepositoryRepository
from app.schemas.response import error_response, success_response
from app.services.engineering_report_service import EngineeringReportService
from app.templates import templates
from app.utils.auth import get_optional_user
from app.utils.deps import get_db

router = APIRouter(tags=["engineering_reports"])


class CreateReportRequest(BaseModel):
    repository_id: int
    from_date: str | None = None
    to_date: str | None = None
    custom_title: str | None = None


class UpdateReportMetadataRequest(BaseModel):
    custom_title: str | None = None


class PublishReportRequest(BaseModel):
    is_repository_anonymized: bool = False
    display_repository_name: str | None = None


def _authenticate(request: Request, db: Session):
    return get_optional_user(request, db)


def _login_redirect() -> Response:
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(settings.session_cookie_name)
    return response


@router.get("/tools/reports", response_class=HTMLResponse, response_model=None)
async def reports_page(request: Request, db: Session = Depends(get_db)) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()

    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    reports = EngineeringReportRepository(db).list_by_user(user.id, page=1, per_page=50)
    return templates.TemplateResponse(
        request=request,
        name="tools/reports.html",
        context={
            "request": request,
            "user": user,
            "repos": repos,
            "reports": reports,
            "active_page": "reports",
        },
    )


@router.get("/api/v1/reports")
async def api_list_reports(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    user = _authenticate(request, db)
    if user is None:
        return JSONResponse(error_response(request, code="UNAUTHORIZED", message="Unauthorized access"), status_code=419)

    reports = EngineeringReportRepository(db).list_by_user(user.id, page=1, per_page=100)
    return JSONResponse(
        success_response(
            request,
            [EngineeringReportService.serialize(report) for report in reports],
        )
    )


@router.post("/api/v1/reports")
async def api_create_report(
    request: Request,
    body: CreateReportRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user = _authenticate(request, db)
    if user is None:
        return JSONResponse(error_response(request, code="UNAUTHORIZED", message="Unauthorized access"), status_code=419)

    report = EngineeringReportService.create_report(
        db,
        user_id=user.id,
        repository_id=body.repository_id,
        from_date=body.from_date,
        to_date=body.to_date,
        custom_title=body.custom_title,
    )
    db.commit()
    return JSONResponse(success_response(request, EngineeringReportService.serialize(report)), status_code=201)


@router.get("/api/v1/reports/{report_id}")
async def api_get_report(
    request: Request,
    report_id: int,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user = _authenticate(request, db)
    if user is None:
        return JSONResponse(error_response(request, code="UNAUTHORIZED", message="Unauthorized access"), status_code=419)

    report = EngineeringReportRepository(db).get_by_user_and_id(user.id, report_id)
    if report is None:
        return JSONResponse(error_response(request, code="NOT_FOUND", message="Report not found"), status_code=404)
    return JSONResponse(success_response(request, EngineeringReportService.serialize(report)))


@router.patch("/api/v1/reports/{report_id}")
async def api_update_report_metadata(
    request: Request,
    report_id: int,
    body: UpdateReportMetadataRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user = _authenticate(request, db)
    if user is None:
        return JSONResponse(error_response(request, code="UNAUTHORIZED", message="Unauthorized access"), status_code=419)

    report = EngineeringReportService.update_metadata(
        db,
        user_id=user.id,
        report_id=report_id,
        custom_title=body.custom_title,
    )
    db.commit()
    return JSONResponse(success_response(request, EngineeringReportService.serialize(report)))


@router.post("/api/v1/reports/{report_id}/publish")
async def api_publish_report(
    request: Request,
    report_id: int,
    body: PublishReportRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user = _authenticate(request, db)
    if user is None:
        return JSONResponse(error_response(request, code="UNAUTHORIZED", message="Unauthorized access"), status_code=419)

    report = EngineeringReportService.publish_report(
        db,
        user_id=user.id,
        report_id=report_id,
        is_repository_anonymized=body.is_repository_anonymized,
        display_repository_name=body.display_repository_name,
    )
    db.commit()
    return JSONResponse(success_response(request, EngineeringReportService.serialize(report)))


@router.post("/api/v1/reports/{report_id}/revoke")
async def api_revoke_report(
    request: Request,
    report_id: int,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user = _authenticate(request, db)
    if user is None:
        return JSONResponse(error_response(request, code="UNAUTHORIZED", message="Unauthorized access"), status_code=419)

    report = EngineeringReportService.revoke_report(db, user_id=user.id, report_id=report_id)
    db.commit()
    return JSONResponse(success_response(request, EngineeringReportService.serialize(report)))


@router.get("/reports/{report_id}/download")
async def download_report_markdown(
    request: Request,
    report_id: int,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()

    report = EngineeringReportRepository(db).get_by_user_and_id(user.id, report_id)
    if report is None:
        return Response("Report not found", status_code=404)

    data = EngineeringReportService.serialize(report)
    content = EngineeringReportService.render_markdown(report)
    filename = f"engineering-report-{report.id}-{data['from_date'][:10]}-{data['to_date'][:10]}.md"
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.delete("/api/v1/reports/{report_id}")
async def api_delete_report(
    request: Request,
    report_id: int,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user = _authenticate(request, db)
    if user is None:
        return JSONResponse(error_response(request, code="UNAUTHORIZED", message="Unauthorized access"), status_code=419)

    report = EngineeringReportService.delete_report(db, user_id=user.id, report_id=report_id)
    db.commit()
    return JSONResponse(success_response(request, EngineeringReportService.serialize(report)))


@router.get("/r/{public_token}", response_class=HTMLResponse, response_model=None)
async def public_report(
    request: Request,
    public_token: str,
    db: Session = Depends(get_db),
) -> Response:
    report = EngineeringReportRepository(db).get_by_public_token(public_token)
    if report is None:
        return Response("Not found", status_code=404, headers={"X-Robots-Tag": "noindex, nofollow"})

    response = templates.TemplateResponse(
        request=request,
        name="public_report.html",
        context={
            "request": request,
            "report": EngineeringReportService.serialize(report, include_private=False),
            "active_page": "",
        },
    )
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response
