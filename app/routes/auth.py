import logging
import secrets
from urllib.parse import urlunsplit

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.templates import templates
from app.core.config import settings
from app.core.exceptions import AuthenticationException
from app.core.session import (
    create_oauth_state_cookie,
    create_session_cookie,
    parse_oauth_state_cookie,
    parse_session_cookie,
)
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService
from app.utils.deps import get_db

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)


def get_current_user(request: Request, db: Session) -> User | None:
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        return None
    try:
        user_id = parse_session_cookie(cookie)
    except AuthenticationException:
        return None
    return UserRepository(db).get_by_id(user_id)


def _localhost_redirect(request: Request) -> RedirectResponse | None:
    if request.url.hostname != "127.0.0.1":
        return None
    netloc = "localhost"
    if request.url.port:
        netloc = f"{netloc}:{request.url.port}"
    target = urlunsplit(
        (
            request.url.scheme,
            netloc,
            request.url.path,
            request.url.query,
            "",
        )
    )
    return RedirectResponse(target, status_code=307)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    canonical_redirect = _localhost_redirect(request)
    if canonical_redirect is not None:
        return canonical_redirect

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "request": request,
            "login_url": "/auth/github/login",
        },
    )


@router.get("/auth/github/login")
async def github_login(
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    canonical_redirect = _localhost_redirect(request)
    if canonical_redirect is not None:
        return canonical_redirect

    state_nonce = secrets.token_urlsafe(32)
    signed_state = create_oauth_state_cookie(state_nonce)
    authorization_url = AuthService(db).build_authorization_url(signed_state)
    response = RedirectResponse(authorization_url, status_code=302)
    response.set_cookie(
        settings.oauth_state_cookie_name,
        signed_state,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=600,
    )
    return response


@router.get("/auth/github/callback")
async def github_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if not code:
        raise AuthenticationException("GitHub OAuth callback is missing code.")
    if not state:
        raise AuthenticationException("GitHub OAuth callback is missing state.")

    state_cookie = request.cookies.get(settings.oauth_state_cookie_name)
    logger.debug(
        "GitHub OAuth callback state presence",
        extra={
            "has_state_cookie": state_cookie is not None,
            "state_query_present": state is not None,
        },
    )
    if not state_cookie:
        raise AuthenticationException("OAuth state cookie is missing.")
    parse_oauth_state_cookie(state_cookie)
    parse_oauth_state_cookie(state)
    if not secrets.compare_digest(state, state_cookie):
        raise AuthenticationException("OAuth state mismatch.")

    user = await AuthService(db).authenticate_callback(code=code, state=state)
    response = RedirectResponse("/repositories", status_code=302)
    response.set_cookie(
        settings.session_cookie_name,
        create_session_cookie(user.id),
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    response.delete_cookie(settings.oauth_state_cookie_name)
    return response


@router.post("/auth/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(settings.session_cookie_name)
    response.delete_cookie(settings.oauth_state_cookie_name)
    return response
