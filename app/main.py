from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging, set_trace_id
from app.routes.api_analytics import router as api_analytics_router
from app.routes.api_ai import router as api_ai_router
from app.routes.api_insights import router as api_insights_router
from app.routes.api_sync import router as api_sync_router
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.explore import router as explore_router
from app.routes.engineering_reports import router as engineering_reports_router
from app.routes.health import router as health_router
from app.routes.repositories import router as repositories_router
from app.routes.tools_release_notes import router as tools_release_notes_router
from app.routes.tools_changelog import router as tools_changelog_router
from app.routes.tools_risks import router as tools_risks_router
from app.services.sync_queue import sync_queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    sync_queue.start()
    try:
        yield
    finally:
        await sync_queue.stop()


def create_app() -> FastAPI:
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def trace_id_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = request.headers.get("x-trace-id") or str(uuid4())
        set_trace_id(trace_id)
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["x-trace-id"] = trace_id
        return response

    register_exception_handlers(app)

    app.include_router(auth_router)
    app.include_router(repositories_router)
    app.include_router(dashboard_router)
    app.include_router(api_analytics_router)
    app.include_router(api_ai_router)
    app.include_router(api_insights_router)
    app.include_router(api_sync_router)
    app.include_router(explore_router)
    app.include_router(engineering_reports_router)
    app.include_router(health_router)
    app.include_router(tools_release_notes_router)
    app.include_router(tools_changelog_router)
    app.include_router(tools_risks_router)
    return app


app = create_app()
