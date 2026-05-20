from datetime import UTC, datetime
from typing import Any

from fastapi import Request


def _trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", "-")


def build_meta(request: Request) -> dict[str, Any]:
    return {
        "trace_id": _trace_id(request),
        "timestamp": datetime.now(UTC).isoformat(),
    }


def success_response(request: Request, data: Any) -> dict[str, Any]:
    return {
        "data": data,
        "error": None,
        "meta": build_meta(request),
    }


def error_response(
    request: Request,
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "meta": build_meta(request),
    }
