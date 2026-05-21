from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app


def _client() -> TestClient:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session)
    session = factory()
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_public_pages_render_without_login() -> None:
    client = _client()
    routes = ["/login", "/explore", "/developer-news", "/ai-tools", "/health"]

    for route in routes:
        response = client.get(route, follow_redirects=False)
        assert response.status_code == 200, route


def test_private_pages_require_login() -> None:
    client = _client()
    routes = [
        "/repositories",
        "/dashboard",
        "/dashboard/global",
        "/team",
        "/sync-status",
        "/account",
        "/settings",
    ]

    for route in routes:
        response = client.get(route, follow_redirects=False)
        assert response.status_code == 302, route
        assert response.headers["location"] == "/login"


def test_analytics_and_workspace_apis_require_login() -> None:
    client = _client()

    analytics_response = client.get("/api/v1/analytics/1/overview")
    ai_response = client.post("/api/v1/ai/commit-message", json={"diff": ""})

    assert analytics_response.status_code == 401
    assert ai_response.status_code == 401
