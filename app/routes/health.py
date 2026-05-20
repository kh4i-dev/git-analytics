from fastapi import APIRouter, Request

from app.schemas.response import success_response

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(request: Request) -> dict[str, object]:
    return success_response(
        request,
        data={
            "status": "ok",
            "service": "git-analytics",
        },
    )
