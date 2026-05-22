import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from sqlalchemy.orm import Session
from app.templates import templates
from app.core.config import settings
from app.repositories import RepositoryRepository
from app.schemas.response import success_response
from app.services.explore_service import ExploreService
from app.utils.auth import get_optional_user
from app.utils.deps import get_db

router = APIRouter(tags=["explore"])


def _authenticate(request: Request, db: Session):
    return get_optional_user(request, db)


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
