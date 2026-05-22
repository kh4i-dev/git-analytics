import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session
from app.clients.github_client import GitHubClient
from app.templates import templates
from app.core.config import settings
from app.core.security import decrypt_token
from app.models.user import User
from app.repositories import RepositoryRepository, SyncJobRepository
from app.services.ai_settings_service import AiSettingsService
from app.services.analytics_service import AnalyticsService
from app.services.insights_service import InsightsService
from app.utils.deps import get_db
from app.utils.auth import get_optional_user
from app.utils.timezone import VN_TZ, now_utc, utc_to_vn

router = APIRouter(tags=["dashboard"])
logger = logging.getLogger(__name__)


def _authenticate(request: Request, db: Session) -> User | None:
    return get_optional_user(request, db)


def _login_redirect() -> Response:
    r = RedirectResponse("/login", status_code=302)
    r.delete_cookie(settings.session_cookie_name)
    return r


def _get_repo_or_none(db: Session, user_id: int, repo_id: int):
    return RepositoryRepository(db).get_by_user_and_id(user_id, repo_id)


@router.get("/dashboard", response_class=HTMLResponse, response_model=None)
@router.get("/dashboard/global", response_class=HTMLResponse, response_model=None)
async def global_dashboard(
    request: Request,
    branch: str | None = None,
    contributor: str | None = None,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    stats = AnalyticsService(db).get_global_overview(user.id, branch=branch, contributor=contributor)
    return templates.TemplateResponse(
        request=request,
        name="dashboard_global.html",
        context={
            "request": request,
            "user": user,
            "repos": repos,
            "stats": stats,
            "active_page": "global_dashboard",
        },
    )


@router.get("/settings", response_class=HTMLResponse, response_model=None)
async def settings_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "request": request,
            "user": user,
            "repos": repos,
            "active_page": "settings",
            "is_local_dev": settings.is_local_workspace,
        },
    )


@router.get("/onboarding", response_class=HTMLResponse, response_model=None)
async def onboarding_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    return templates.TemplateResponse(
        request=request,
        name="onboarding.html",
        context={
            "request": request,
            "user": user,
            "repos": repos,
            "active_page": "onboarding",
        },
    )


@router.post("/settings/repositories/{repo_id}/branches")
async def update_repository_branch_settings(
    request: Request,
    repo_id: int,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()
    repo = RepositoryRepository(db).get_by_user_and_id(user.id, repo_id)
    if repo is None:
        return RedirectResponse("/settings?error=repo_not_found", status_code=302)

    form = await request.form()
    mode = str(form.get("branch_sync_mode") or "default_only")
    if mode not in {"default_only", "selected", "all"}:
        mode = "default_only"
    selected = [
        item.strip()
        for item in str(form.get("selected_branches") or "").split(",")
        if item.strip()
    ]
    RepositoryRepository(db).update(
        repo,
        {
            "branch_sync_mode": mode,
            "selected_branches": ",".join(selected) if selected else None,
        },
    )
    db.commit()
    return RedirectResponse("/settings?branch_settings=updated", status_code=302)


@router.get("/account", response_class=HTMLResponse, response_model=None)
async def account_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    return templates.TemplateResponse(
        request=request,
        name="account.html",
        context={
            "request": request,
            "user": user,
            "repos": repos,
            "active_page": "account",
        },
    )


@router.get("/sync-status", response_class=HTMLResponse, response_model=None)
async def sync_status_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    
    # Calculate sync durations and statistics
    total = len(repos)
    success_count = sum(1 for r in repos if r.last_sync_status == "success")
    failed_count = sum(1 for r in repos if r.last_sync_status == "failed")
    syncing_count = sum(1 for r in repos if r.last_sync_status == "syncing")
    
    durations = []
    for r in repos:
        r.duration_str = "—"
        if r.last_synced_at and r.sync_started_at:
            if r.last_synced_at > r.sync_started_at:
                delta = r.last_synced_at - r.sync_started_at
                seconds = int(delta.total_seconds())
                durations.append(seconds)
                r.duration_str = f"{seconds}s"
            elif r.last_sync_status == "syncing":
                # currently running
                delta = now_utc() - utc_to_vn(r.sync_started_at).astimezone(VN_TZ)
                seconds = max(0, int(delta.total_seconds()))
                r.duration_str = f"{seconds}s (chạy)"
    
    avg_duration_str = "—"
    if durations:
        avg_duration_str = f"{int(sum(durations) / len(durations))}s"
        
    sync_stats = {
        "total": total,
        "success_count": success_count,
        "failed_count": failed_count,
        "syncing_count": syncing_count,
        "avg_duration_str": avg_duration_str,
    }
    sync_jobs = SyncJobRepository(db).list_recent_by_user(user.id, limit=30)
    job_summary = {
        "queued": sum(1 for job in sync_jobs if job.status == "queued"),
        "running": sum(1 for job in sync_jobs if job.status == "running"),
        "failed": sum(1 for job in sync_jobs if job.status == "failed"),
    }
    
    # Fetch GitHub API Rate Limit
    rate_limit = {"limit": 5000, "remaining": 5000, "reset_time_local": "N/A"}
    try:
        token = decrypt_token(user.encrypted_github_token)
        async with GitHubClient(token) as client:
            rl_data = await client.get_rate_limit()
            rate_limit["limit"] = rl_data.get("limit") or 5000
            rate_limit["remaining"] = rl_data.get("remaining") or 5000
            if rl_data.get("reset_at"):
                dt = datetime.fromisoformat(rl_data["reset_at"].replace("Z", "+00:00"))
                rate_limit["reset_time_local"] = utc_to_vn(dt).strftime("%H:%M:%S")
    except Exception as e:
        logger.warning(f"Failed to fetch rate limit in sync_status_page: {e}")
        
    return templates.TemplateResponse(
        request=request,
        name="sync_status.html",
        context={
            "request": request,
            "user": user,
            "repos": repos,
            "rate_limit": rate_limit,
            "sync_stats": sync_stats,
            "sync_jobs": sync_jobs,
            "job_summary": job_summary,
            "active_page": "sync_status",
        },
    )


@router.get("/developer-news", response_class=HTMLResponse, response_model=None)
async def developer_news_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100) if user else []
    return templates.TemplateResponse(
        request=request,
        name="developer_news.html",
        context={
            "request": request,
            "user": user,
            "repos": repos,
            "active_page": "developer_news",
            "base_template": "layouts/dashboard_base.html" if user else "layouts/public_base.html",
        },
    )


@router.get("/ai-tools", response_class=HTMLResponse, response_model=None)
async def ai_tools_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100) if user else []
    ai_settings = AiSettingsService(db).get_settings(user.id) if user else None
    ai_enabled = bool(
        user
        and ai_settings
        and (
            (ai_settings["mode"] == "cloud" and ai_settings["cloud_available"])
            or any(item["has_key"] for item in ai_settings["providers"])
        )
    )
    return templates.TemplateResponse(
        request=request,
        name="ai_tools.html",
        context={
            "request": request,
            "user": user,
            "repos": repos,
            "active_page": "ai_tools",
            "base_template": "layouts/dashboard_base.html" if user else "layouts/public_base.html",
            "is_public": user is None,
            "ai_enabled": ai_enabled,
            "ai_message": "Configure BYOK or Cloud AI in Settings before using AI tools.",
        },
    )


@router.get("/team", response_class=HTMLResponse, response_model=None)
async def team_members_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    stats = AnalyticsService(db).get_global_overview(user.id)
    return templates.TemplateResponse(
        request=request,
        name="team_members.html",
        context={
            "request": request,
            "user": user,
            "repos": repos,
            "stats": stats,
            "active_page": "team",
        },
    )


@router.get("/team/{username}", response_class=HTMLResponse, response_model=None)
async def team_member_profile_page(
    request: Request,
    username: str,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    try:
        profile = AnalyticsService(db).get_contributor_profile(user.id, username)
    except Exception:
        return RedirectResponse("/team", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="team_member_profile.html",
        context={
            "request": request,
            "user": user,
            "repos": repos,
            "profile": profile,
            "active_page": "team",
        },
    )


@router.get("/dashboard/{repo_id}", response_class=HTMLResponse, response_model=None)
async def dashboard_overview(
    request: Request,
    repo_id: int,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()
    repo = _get_repo_or_none(db, user.id, repo_id)
    if repo is None:
        return RedirectResponse("/repositories", status_code=302)
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    return templates.TemplateResponse(
        request=request,
        name="dashboard_overview.html",
        context={
            "request": request,
            "user": user,
            "repo": repo,
            "repos": repos,
            "active_page": "overview",
        },
    )


@router.get("/dashboard/{repo_id}/commits", response_class=HTMLResponse, response_model=None)
async def dashboard_commits(
    request: Request,
    repo_id: int,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()
    repo = _get_repo_or_none(db, user.id, repo_id)
    if repo is None:
        return RedirectResponse("/repositories", status_code=302)
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    return templates.TemplateResponse(
        request=request,
        name="dashboard_commits.html",
        context={
            "request": request,
            "user": user,
            "repo": repo,
            "repos": repos,
            "active_page": "commits",
        },
    )


@router.get(
    "/dashboard/{repo_id}/pull-requests",
    response_class=HTMLResponse,
    response_model=None,
)
async def dashboard_pull_requests(
    request: Request,
    repo_id: int,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()
    repo = _get_repo_or_none(db, user.id, repo_id)
    if repo is None:
        return RedirectResponse("/repositories", status_code=302)
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    return templates.TemplateResponse(
        request=request,
        name="dashboard_pull_requests.html",
        context={
            "request": request,
            "user": user,
            "repo": repo,
            "repos": repos,
            "active_page": "pull_requests",
        },
    )


@router.get("/dashboard/{repo_id}/issues", response_class=HTMLResponse, response_model=None)
async def dashboard_issues(
    request: Request,
    repo_id: int,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()
    repo = _get_repo_or_none(db, user.id, repo_id)
    if repo is None:
        return RedirectResponse("/repositories", status_code=302)
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    return templates.TemplateResponse(
        request=request,
        name="dashboard_issues.html",
        context={
            "request": request,
            "user": user,
            "repo": repo,
            "repos": repos,
            "active_page": "issues",
        },
    )


@router.get("/dashboard/{repo_id}/insights", response_class=HTMLResponse, response_model=None)
async def dashboard_insights(
    request: Request,
    repo_id: int,
    db: Session = Depends(get_db),
) -> Response:
    user = _authenticate(request, db)
    if user is None:
        return _login_redirect()
    repo = _get_repo_or_none(db, user.id, repo_id)
    if repo is None:
        return RedirectResponse("/repositories", status_code=302)
    repos = RepositoryRepository(db).list_by_user(user.id, page=1, per_page=100)
    return templates.TemplateResponse(
        request=request,
        name="dashboard_insights.html",
        context={
            "request": request,
            "user": user,
            "repo": repo,
            "repos": repos,
            "active_page": "insights",
        },
    )
