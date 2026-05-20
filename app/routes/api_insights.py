import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationException
from app.core.session import parse_session_cookie
from app.db.session import get_db
from app.repositories import UserRepository
from app.schemas.response import error_response, success_response
from app.services.insights_service import InsightsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/insights", tags=["Insights"])


def _get_user_id(request: Request, db) -> int:
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        raise AuthenticationException("Authentication required.")
    user_id = parse_session_cookie(cookie)
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise AuthenticationException("User not found.")
    return user_id


@router.get("/{repo_id}")
async def api_insights(
    request: Request,
    repo_id: int,
    branch: str | None = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = _get_user_id(request, db)
    data = InsightsService(db).get_insights(user_id, repo_id, branch)
    return JSONResponse(success_response(request, data))
