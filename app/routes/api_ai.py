from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.schemas.response import success_response
from app.services.ai_provider_service import AiToolService
from app.utils.auth import require_user_id
from app.utils.deps import get_db

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


class DiffRequest(BaseModel):
    diff: str = Field(max_length=60_000)


class AssistantRequest(BaseModel):
    question: str = Field(max_length=60_000)


@router.post("/commit-message")
async def ai_commit_message(
    request: Request,
    body: DiffRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = require_user_id(request, db)
    data = await AiToolService(db).generate_commit_message(
        user_id=user_id,
        diff=body.diff,
    )
    return JSONResponse(success_response(request, data))


@router.post("/review")
async def ai_review(
    request: Request,
    body: DiffRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = require_user_id(request, db)
    data = await AiToolService(db).review_diff(user_id=user_id, diff=body.diff)
    return JSONResponse(success_response(request, data))


@router.post("/assistant")
async def ai_assistant(
    request: Request,
    body: AssistantRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = require_user_id(request, db)
    data = await AiToolService(db).answer_question(
        user_id=user_id,
        question=body.question,
    )
    return JSONResponse(success_response(request, data))
