from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import settings as global_settings
from app.core.security import decrypt_token, encrypt_token
from app.core.session import create_session_cookie
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.repositories import AiSettingsRepository, UserRepository


def _client() -> tuple[TestClient, Session, int]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session)
    session = factory()
    user = UserRepository(session).create(
        {
            "github_id": 1001,
            "github_login": "octo",
            "encrypted_github_token": encrypt_token(
                "github-token",
                encryption_key=global_settings.encryption_key,
            ),
        },
    )
    session.commit()
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", create_session_cookie(user.id))
    return client, session, user.id


def test_ai_settings_require_authentication() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/settings/ai")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_save_byok_key_encrypts_and_masks_response() -> None:
    client, db, user_id = _client()
    response = client.put(
        "/api/settings/ai",
        json={
            "mode": "byok",
            "default_provider": "openai",
            "keys": {"openai": "sk-test-secret"},
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["mode"] == "byok"
    assert data["default_provider"] == "openai"
    openai = next(item for item in data["providers"] if item["provider"] == "openai")
    assert openai["has_key"] is True
    assert openai["masked_key"] == "********"
    assert "sk-test-secret" not in response.text

    row = AiSettingsRepository(db).get_by_user_mode_provider(user_id, "byok", "openai")
    assert row is not None
    assert row.encrypted_api_key != "sk-test-secret"
    assert decrypt_token(row.encrypted_api_key) == "sk-test-secret"


def test_cloud_mode_requires_configured_server_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(global_settings, "openai_api_key", None)
    monkeypatch.setattr(global_settings, "gemini_api_key", None)
    monkeypatch.setattr(global_settings, "claude_api_key", None)
    client, _db, _user_id = _client()
    response = client.put(
        "/api/settings/ai",
        json={"mode": "cloud", "default_provider": "openai", "keys": {}},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_save_byok_key_nvidia_valid() -> None:
    client, db, user_id = _client()
    response = client.put(
        "/api/settings/ai",
        json={
            "mode": "byok",
            "default_provider": "nvidia",
            "keys": {"nvidia": "sk-test-secret"},
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["mode"] == "byok"
    assert data["default_provider"] == "nvidia"
    nvidia = next(item for item in data["providers"] if item["provider"] == "nvidia")
    assert nvidia["has_key"] is True
    assert nvidia["masked_key"] == "********"


def test_save_byok_key_nvidia_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockResponse:
        status_code = 401
        text = "Unauthorized"
    
    class MockClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def get(self, url, headers=None):
            return MockResponse()

    import httpx
    monkeypatch.setattr(httpx, "Client", MockClient)

    client, _db, _user_id = _client()
    response = client.put(
        "/api/settings/ai",
        json={
            "mode": "byok",
            "default_provider": "nvidia",
            "keys": {"nvidia": "invalid-real-key-format"},
        },
    )

    assert response.status_code == 400
    assert "validation failed" in response.json()["error"]["message"].lower()
