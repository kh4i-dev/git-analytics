import os
import tempfile
from collections.abc import Generator
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.config import settings as global_settings
from app.core.security import encrypt_token
from app.core.session import create_session_cookie
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.repositories import UserRepository


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    _, db_path = tempfile.mkstemp(suffix=".db")
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except PermissionError:
            pass


def _make_user(db: Session) -> tuple[UserRepository, str]:
    token = encrypt_token("gh-token", encryption_key=global_settings.encryption_key)
    user = UserRepository(db).create({
        "github_id": 4001,
        "github_login": "exploreuser",
        "encrypted_github_token": token,
    })
    db.commit()
    return user, create_session_cookie(user.id)


def _test_client(db: Session) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: (yield db)
    return TestClient(app)


# ── Auth Checks ──────────────────────────────────────────────────────────────

def test_explore_page_is_public(db_session: Session) -> None:
    client = _test_client(db_session)
    response = client.get("/explore", follow_redirects=False)
    assert response.status_code == 200
    assert "Git Analytics" in response.text


@patch("app.services.explore_service.ExploreService.get_explore_data", new_callable=AsyncMock)
def test_api_explore_trending_is_public(
    mock_explore: AsyncMock,
    db_session: Session,
) -> None:
    mock_explore.return_value = {"trending_repos": [], "hn_news": [], "ai_tools": []}
    client = _test_client(db_session)
    response = client.get("/api/v1/explore/trending")
    assert response.status_code == 200


# ── Mocked Explore Flow ───────────────────────────────────────────────────────

@patch("app.clients.explore_client.fetch_trending_repos", new_callable=AsyncMock)
@patch("app.clients.explore_client.fetch_hn_news", new_callable=AsyncMock)
@patch("app.clients.explore_client.fetch_ai_tools", new_callable=AsyncMock)
def test_explore_api_contract(
    mock_ai: AsyncMock,
    mock_hn: AsyncMock,
    mock_trending: AsyncMock,
    db_session: Session,
) -> None:
    # Setup mocks
    mock_trending.return_value = [
        {
            "id": 12345,
            "full_name": "test/trending",
            "name": "trending",
            "owner_login": "test",
            "owner_avatar": "https://example.com/avatar",
            "description": "Amazing project",
            "language": "Python",
            "stars": 1500,
            "forks": 250,
            "topics": ["python", "fastapi"],
            "html_url": "https://github.com/test/trending",
        }
    ]
    mock_hn.return_value = [
        {
            "id": 999123,
            "title": "Show HN: Git Analytics V2",
            "url": "https://news.ycombinator.com/item?id=999123",
            "score": 120,
            "by": "dang",
            "time": 1716246000,
            "comments": 35,
            "hn_url": "https://news.ycombinator.com/item?id=999123",
        }
    ]
    mock_ai.return_value = [
        {
            "id": 888999,
            "full_name": "agent/ai-agent-framework",
            "name": "ai-agent-framework",
            "owner_login": "agent",
            "owner_avatar": "https://example.com/avatar2",
            "description": "Unbelievable framework",
            "language": "TypeScript",
            "stars": 4200,
            "forks": 510,
            "topics": ["ai", "agents"],
            "html_url": "https://github.com/agent/ai-agent-framework",
        }
    ]

    client = _test_client(db_session)

    # Reset ExploreService cache entries to force fresh mocked calls
    from app.services.explore_service import _cache
    _cache["trending"] = {}
    _cache["hn_news"] = (None, 0.0)
    _cache["ai_tools"] = (None, 0.0)

    # 1. Check HTML template renders correctly for public access
    response_html = client.get("/explore")
    assert response_html.status_code == 200
    assert "Git Analytics" in response_html.text
    assert "Xu h" in response_html.text

    # 2. Check JSON data response structure matches exact client models
    response_json = client.get("/api/v1/explore/trending?language=python&days=7")
    assert response_json.status_code == 200
    data = response_json.json()["data"]

    assert "trending_repos" in data
    assert "hn_news" in data
    assert "ai_tools" in data

    assert data["trending_repos"][0]["full_name"] == "test/trending"
    assert data["hn_news"][0]["title"] == "Show HN: Git Analytics V2"
    assert data["ai_tools"][0]["name"] == "ai-agent-framework"
