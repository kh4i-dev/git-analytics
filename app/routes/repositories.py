import logging
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session
from app.clients.github_client import GitHubClient
from app.templates import templates
from app.core.config import settings
from app.core.exceptions import AppException, AuthenticationException
from app.core.security import decrypt_token
from app.core.session import parse_session_cookie
from app.models.user import User
from app.repositories import RepositoryRepository, UserRepository
from app.services.sync_service import SyncService
from app.utils.deps import get_db

router = APIRouter(tags=["repositories"])


def _authenticate(request: Request, db: Session) -> User | None:
    session_cookie = request.cookies.get(settings.session_cookie_name)
    if not session_cookie:
        return None
    try:
        user_id = parse_session_cookie(session_cookie)
    except AuthenticationException:
        return None
    return UserRepository(db).get_by_id(user_id)


def _login_redirect() -> Response:
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(settings.session_cookie_name)
    return response


@router.get("/repositories", response_class=HTMLResponse, response_model=None)
async def repositories_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()

    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)

    return templates.TemplateResponse(
        request=request,
        name="repositories.html",
        context={
            "request": request,
            "user": user,
            "github_username": user.github_login,
            "repositories": repos,
            "repos": repos,
            "active_page": "repositories",
        },
    )


@router.post("/repositories/import")
async def import_repositories(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()

    try:
        token = decrypt_token(user.encrypted_github_token)
    except Exception:
        response = RedirectResponse("/repositories?error=token_decrypt_failed", status_code=302)
        return response

    client = GitHubClient(token)
    try:
        raw_repos = await client.list_user_repositories()
    except AppException as exc:
        await client.aclose()
        response = RedirectResponse(f"/repositories?error=import_failed&message={exc.message}", status_code=302)
        return response
    except Exception:
        await client.aclose()
        response = RedirectResponse("/repositories?error=import_failed&message=GitHub API request failed.", status_code=302)
        return response

    await client.aclose()

    repo_repo = RepositoryRepository(db)
    imported = 0
    for raw in raw_repos:
        owner = raw.get("owner", {})
        repo_repo.upsert_by_user_github_repo_id(
            user_id=user.id,
            github_repo_id=raw["id"],
            data={
                "owner": owner.get("login") if isinstance(owner, dict) else str(owner),
                "name": raw["name"],
                "full_name": raw["full_name"],
                "is_private": bool(raw.get("private", False)),
                "default_branch": raw.get("default_branch"),
                "html_url": raw["html_url"],
            },
        )
        imported += 1

    db.commit()

    return RedirectResponse(f"/repositories?imported={imported}", status_code=302)


@router.post("/repositories/{repo_id}/sync")
async def sync_repository(
    request: Request,
    repo_id: int,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()

    service = SyncService(db)
    try:
        result = await service.sync_repository(user_id=user.id, repo_id=repo_id)
        return RedirectResponse(
            f"/repositories?synced=1&mode={result.mode}&status={result.status}",
            status_code=302,
        )
    except AppException as exc:
        return RedirectResponse(
            f"/repositories?error=sync_failed&message={quote(exc.message)}",
            status_code=302,
        )
    except Exception as exc:
        return RedirectResponse(
            f"/repositories?error=sync_failed&message={quote(str(exc)[:200])}",
            status_code=302,
        )


@router.post("/repositories/sync-all")
async def sync_all_repositories(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()

    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    if not repos:
        return RedirectResponse("/repositories?error=no_repositories", status_code=302)

    service = SyncService(db)
    success_count = 0
    failed_count = 0
    last_mode = "incremental"
    last_error: str | None = None

    for repo in repos:
        if repo.last_sync_status == "syncing":
            continue
        try:
            result = await service.sync_repository(user_id=user.id, repo_id=repo.id)
            success_count += 1
            last_mode = result.mode
        except AppException as exc:
            failed_count += 1
            last_error = exc.message
        except Exception as exc:
            failed_count += 1
            last_error = str(exc)[:200]

    if success_count:
        return RedirectResponse(
            f"/repositories?synced_all={success_count}&failed={failed_count}&mode={last_mode}&status=success",
            status_code=302,
        )

    message = quote(last_error or "Không thể cập nhật repository.")
    return RedirectResponse(
        f"/repositories?error=sync_failed&message={message}",
        status_code=302,
    )
