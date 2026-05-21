import logging
from typing import Any
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.templates import templates
from app.core.config import settings
from app.core.exceptions import AuthenticationException
from app.core.session import parse_session_cookie
from app.repositories import UserRepository, RepositoryRepository
from app.services.risk_insight_service import RiskInsightService
from app.schemas.response import success_response, error_response
from app.utils.deps import get_db

router = APIRouter(tags=["tools_risks"])

def _authenticate(request: Request, db: Session):
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        return None
    try:
        user_id = parse_session_cookie(cookie)
    except AuthenticationException:
        return None
    return UserRepository(db).get_by_id(user_id)

def _login_redirect() -> Response:
    r = RedirectResponse("/login", status_code=302)
    r.delete_cookie(settings.session_cookie_name)
    return r

@router.get("/tools/risks", response_class=HTMLResponse, response_model=None)
async def risks_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()

    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)

    return templates.TemplateResponse(
        request=request,
        name="tools/risks.html",
        context={
            "request": request,
            "user": user,
            "repos": repos,
            "active_page": "risks",
        },
    )

@router.get("/api/v1/tools/risks")
async def api_get_risks(
    request: Request,
    repo_id: int | None = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user = _authenticate(request, db)
    if user is None:
        return JSONResponse(error_response(request, code="UNAUTHORIZED", message="Unauthorized access"), status_code=419)

    if repo_id:
        repo = RepositoryRepository(db).get_by_id(repo_id)
        if not repo or repo.user_id != user.id:
            return JSONResponse(error_response(request, code="NOT_FOUND", message="Repository not found"), status_code=404)

    risks = RiskInsightService.detect_risks(db=db, user_id=user.id, repo_id=repo_id)
    return JSONResponse(success_response(request, risks))

@router.get("/api/v1/tools/risks/summary")
async def api_get_risk_summary(
    request: Request,
    repo_id: int | None = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user = _authenticate(request, db)
    if user is None:
        return JSONResponse(error_response(request, code="UNAUTHORIZED", message="Unauthorized access"), status_code=419)

    if repo_id:
        repo = RepositoryRepository(db).get_by_id(repo_id)
        if not repo or repo.user_id != user.id:
            return JSONResponse(error_response(request, code="NOT_FOUND", message="Repository not found"), status_code=404)

    summary = RiskInsightService.get_risk_summary(db=db, user_id=user.id, repo_id=repo_id)
    return JSONResponse(success_response(request, summary))
