from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationException
from app.core.session import parse_session_cookie
from app.repositories import UserRepository
from app.schemas.response import error_response, success_response
from app.services.ai_settings_service import AiSettingsService
from app.utils.deps import get_db

router = APIRouter(prefix="/api/settings", tags=["Settings"])


def _require_user_id(request: Request, db: Session) -> int:
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        raise AuthenticationException()
    user_id = parse_session_cookie(cookie)
    if UserRepository(db).get_by_id(user_id) is None:
        raise AuthenticationException()
    return user_id


@router.get("/ai")
async def get_ai_settings(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    user_id = _require_user_id(request, db)
    data = AiSettingsService(db).get_settings(user_id)
    return JSONResponse(success_response(request, data))


@router.put("/ai")
async def update_ai_settings(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    user_id = _require_user_id(request, db)
    payload = await request.json()
    if not isinstance(payload, dict):
        return JSONResponse(
            error_response(
                request,
                code="VALIDATION_ERROR",
                message="The request is invalid.",
            ),
            status_code=400,
        )
    data = AiSettingsService(db).update_settings(user_id, payload)
    return JSONResponse(success_response(request, data))


@router.delete("/ai/provider/{provider}")
async def delete_ai_provider_key(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = _require_user_id(request, db)
    data = AiSettingsService(db).delete_provider_key(user_id, provider)
    return JSONResponse(success_response(request, data))


@router.delete("/ai/keys")
async def delete_ai_provider_keys(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = _require_user_id(request, db)
    data = AiSettingsService(db).delete_all_byok_keys(user_id)
    return JSONResponse(success_response(request, data))
