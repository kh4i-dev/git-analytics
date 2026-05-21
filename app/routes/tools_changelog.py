import logging
from typing import Any
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.templates import templates
from app.core.config import settings
from app.core.exceptions import AuthenticationException
from app.core.session import parse_session_cookie
from app.repositories import UserRepository, RepositoryRepository
from app.services.changelog_service import ChangelogService
from app.schemas.response import success_response, error_response
from app.utils.deps import get_db

router = APIRouter(tags=["tools_changelog"])

class ChangelogRequest(BaseModel):
    repo_id: int
    branch: str | None = None
    from_date: str | None = None
    to_date: str | None = None
    group_by: str = "week"

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

@router.get("/tools/changelog", response_class=HTMLResponse, response_model=None)
async def changelog_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()

    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)

    return templates.TemplateResponse(
        request=request,
        name="tools/changelog.html",
        context={
            "request": request,
            "user": user,
            "repos": repos,
            "active_page": "changelog",
        },
    )

@router.post("/api/v1/tools/changelog")
async def api_generate_changelog(
    request: Request,
    body: ChangelogRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user = _authenticate(request, db)
    if user is None:
        return JSONResponse(error_response(request, code="UNAUTHORIZED", message="Unauthorized access"), status_code=419)

    repo = RepositoryRepository(db).get_by_id(body.repo_id)
    if not repo or repo.user_id != user.id:
        return JSONResponse(error_response(request, code="NOT_FOUND", message="Repository not found"), status_code=404)

    data = ChangelogService.generate_changelog(
        db=db,
        repo_id=body.repo_id,
        branch=body.branch,
        from_date=body.from_date,
        to_date=body.to_date,
        group_by=body.group_by
    )
    return JSONResponse(success_response(request, data))

@router.get("/tools/changelog/download")
async def download_changelog(
    request: Request,
    repo_id: int,
    branch: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    group_by: str = "week",
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()

    repo = RepositoryRepository(db).get_by_id(repo_id)
    if not repo or repo.user_id != user.id:
        return Response("Repository not found", status_code=404)

    data = ChangelogService.generate_changelog(
        db=db,
        repo_id=repo_id,
        branch=branch,
        from_date=from_date,
        to_date=to_date,
        group_by=group_by
    )
    
    return Response(
        content=data["markdown"],
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=CHANGELOG.md"}
    )
