import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from sqlalchemy.orm import Session
from app.templates import templates
from app.core.config import settings
from app.core.exceptions import AuthenticationException
from app.core.session import parse_session_cookie
from app.repositories import RepositoryRepository, UserRepository
from app.schemas.response import success_response
from app.services.explore_service import ExploreService
from app.utils.deps import get_db

router = APIRouter(tags=["explore"])


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


@router.get("/explore", response_class=HTMLResponse, response_model=None)
async def explore_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100) if user else []
    repo = repos[0] if repos else None

    return templates.TemplateResponse(
        request=request,
        name="explore.html",
        context={
            "request": request,
            "user": user,
            "repo": repo,
            "repos": repos,
            "active_page": "explore",
            "base_template": "layouts/public_base.html" if user is None else "layouts/dashboard_base.html",
        },
    )


@router.get("/api/v1/explore/trending")
async def api_explore_trending(
    request: Request,
    language: str | None = None,
    days: int = 7,
    db: Session = Depends(get_db),
) -> JSONResponse:
    data = await ExploreService.get_explore_data(language=language, days=days)
    return JSONResponse(success_response(request, data))
