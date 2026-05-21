from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationException
from app.core.session import parse_session_cookie
from app.repositories import UserRepository
from app.schemas.response import error_response, success_response
from app.utils.deps import get_db

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


@router.post("/commit-message")
async def ai_commit_message(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    blocked = _require_local_workspace(request, db)
    if blocked is not None:
        return blocked
    payload = await request.json()
    diff = str(payload.get("diff") or "")
    files = _changed_files(diff)
    prefix = _commit_prefix(diff, files)
    scope = _scope_from_files(files)
    summary = _summary_from_diff(diff, files)
    message = f"{prefix}{f'({scope})' if scope else ''}: {summary}"
    return JSONResponse(success_response(request, {"message": message, "files": files[:12]}))


@router.post("/review")
async def ai_review(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    blocked = _require_local_workspace(request, db)
    if blocked is not None:
        return blocked
    payload = await request.json()
    diff = str(payload.get("diff") or "")
    findings = []
    lowered = diff.lower()
    if any(token in lowered for token in ["password", "secret", "token", "api_key"]):
        findings.append({"type": "security", "title": "Sensitive value risk", "detail": "Diff có dấu hiệu chứa secret hoặc token. Nên chuyển sang biến môi trường hoặc secret manager."})
    if "except exception" in lowered or "except:" in lowered:
        findings.append({"type": "reliability", "title": "Broad exception handling", "detail": "Exception quá rộng có thể che lỗi thật. Nên bắt lỗi cụ thể và log đủ ngữ cảnh."})
    if "select(" in lowered and ".limit(" not in lowered and "all()" in lowered:
        findings.append({"type": "performance", "title": "Unbounded query", "detail": "Query có thể trả quá nhiều bản ghi. Cân nhắc phân trang hoặc giới hạn rõ ràng."})
    if not findings:
        findings.append({"type": "architecture", "title": "Chưa thấy rủi ro nổi bật", "detail": "Local Mode chưa phát hiện pattern nguy hiểm. Vẫn nên review logic nghiệp vụ và test coverage."})
    return JSONResponse(success_response(request, {"findings": findings, "files": _changed_files(diff)[:12]}))


@router.post("/assistant")
async def ai_assistant(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    blocked = _require_local_workspace(request, db)
    if blocked is not None:
        return blocked
    payload = await request.json()
    question = str(payload.get("question") or "").strip()
    answer = _answer_from_repo_context(question)
    return JSONResponse(success_response(request, {"answer": answer, "mode": "local_workspace"}))


def _require_local_workspace(request: Request, db: Session) -> JSONResponse | None:
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        return JSONResponse(
            error_response(
                request,
                code="AUTHENTICATION_REQUIRED",
                message="Đăng nhập để sử dụng AI Tools với repository của bạn.",
            ),
            status_code=401,
        )
    try:
        user_id = parse_session_cookie(cookie)
    except AuthenticationException:
        return JSONResponse(
            error_response(
                request,
                code="AUTHENTICATION_REQUIRED",
                message="Đăng nhập để sử dụng AI Tools với repository của bạn.",
            ),
            status_code=401,
        )
    if UserRepository(db).get_by_id(user_id) is None:
        return JSONResponse(
            error_response(
                request,
                code="AUTHENTICATION_REQUIRED",
                message="Đăng nhập để sử dụng AI Tools với repository của bạn.",
            ),
            status_code=401,
        )
    if not settings.is_local_workspace:
        return JSONResponse(
            error_response(
                request,
                code="LOCAL_WORKSPACE_REQUIRED",
                message="Tính năng này chỉ khả dụng khi chạy Git Analytics ở chế độ Local Workspace.",
            ),
            status_code=403,
        )
    if settings.is_local_workspace:
        return None
    return JSONResponse(
        error_response(
            request,
            code="LOCAL_WORKSPACE_REQUIRED",
            message="Tính năng này chỉ khả dụng khi chạy Git Analytics ở chế độ Local Workspace.",
        ),
        status_code=403,
    )


def _changed_files(diff: str) -> list[str]:
    files = []
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                files.append(parts[3].removeprefix("b/"))
        elif line.startswith("+++ b/"):
            files.append(line[6:])
    return list(dict.fromkeys(files))


def _commit_prefix(diff: str, files: list[str]) -> str:
    lowered = diff.lower()
    if files and all(path.endswith((".md", ".rst")) for path in files):
        return "docs"
    if any("test" in path.lower() for path in files):
        return "test"
    if any(token in lowered for token in ["fix", "bug", "error", "exception", "failed"]):
        return "fix"
    if any(token in lowered for token in ["perf", "cache", "optimi"]):
        return "perf"
    if any(token in lowered for token in ["refactor", "rename", "cleanup"]):
        return "refactor"
    return "feat"


def _scope_from_files(files: list[str]) -> str | None:
    if not files:
        return None
    first = files[0].split("/")
    if len(first) >= 2 and first[0] in {"app", "templates", "tests"}:
        return first[1].replace("_", "-")
    return first[0].replace("_", "-")


def _summary_from_diff(diff: str, files: list[str]) -> str:
    if files:
        filename = files[0].rsplit("/", 1)[-1]
        target = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
        if len(files) > 1:
            return f"update {target} flow and related files"
        return f"update {target} flow"
    additions = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removals = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
    if additions or removals:
        return f"update code path with {additions} additions and {removals} removals"
    return "update implementation"


def _answer_from_repo_context(question: str) -> str:
    lowered = question.lower()
    if "oauth" in lowered or "auth" in lowered:
        return "Auth flow nằm trong `app/routes/auth.py` và `app/services/auth_service.py`. Route tạo GitHub OAuth URL, callback đổi code lấy token, sau đó lưu user/token đã mã hóa qua `UserRepository`."
    if "sync" in lowered or "github" in lowered:
        return "Sync pipeline chạy qua `SyncService`: kiểm tra rate limit, lấy branches/contributors/commits/PR/issues từ GitHub, upsert vào repository layer, rồi cập nhật trạng thái sync. Queue nền nằm ở `app/services/sync_queue.py`."
    if "architecture" in lowered or "kiến trúc" in lowered:
        return "Kiến trúc hiện tại là FastAPI + Jinja + SQLAlchemy. Routes xử lý HTTP, services giữ nghiệp vụ, repositories bọc query DB, models định nghĩa schema. Dashboard đọc analytics qua service/API."
    return "Local Mode trả lời tốt nhất về auth, sync, analytics service, routes và cấu trúc module. Hỏi cụ thể theo flow hoặc file để nhận câu trả lời sát hơn."
