import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.response import success_response
from app.services.insights_service import InsightsService
from app.utils.auth import require_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/insights", tags=["Insights"])


def _get_user_id(request: Request, db) -> int:
    return require_user_id(request, db)


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
