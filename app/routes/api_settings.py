from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.schemas.response import success_response
from app.services.ai_settings_service import AiSettingsService
from app.utils.auth import require_user_id
from app.utils.deps import get_db

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class UpdateAiSettingsRequest(BaseModel):
    mode: str = "byok"
    default_provider: str = "openai"
    keys: dict[str, str] = Field(default_factory=dict)


@router.get("/ai")
async def get_ai_settings(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    user_id = require_user_id(request, db)
    data = AiSettingsService(db).get_settings(user_id)
    return JSONResponse(success_response(request, data))


@router.put("/ai")
async def update_ai_settings(
    request: Request,
    body: UpdateAiSettingsRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = require_user_id(request, db)
    data = AiSettingsService(db).update_settings(user_id, body.model_dump())
    return JSONResponse(success_response(request, data))


@router.delete("/ai/provider/{provider}")
async def delete_ai_provider_key(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = require_user_id(request, db)
    data = AiSettingsService(db).delete_provider_key(user_id, provider)
    return JSONResponse(success_response(request, data))


@router.delete("/ai/keys")
async def delete_ai_provider_keys(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = require_user_id(request, db)
    data = AiSettingsService(db).delete_all_byok_keys(user_id)
    return JSONResponse(success_response(request, data))
