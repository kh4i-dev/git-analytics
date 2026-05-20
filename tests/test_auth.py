import asyncio
from collections.abc import Generator
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.config import Settings
from app.core.exceptions import AuthenticationException
from app.core.security import decrypt_token, generate_encryption_key
from app.core.session import (
    create_oauth_state_cookie,
    create_session_cookie,
    parse_session_cookie,
)
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.user import User
from app.routes.auth import AuthService
from app.services.auth_service import AuthService as AuthServiceClass


def run_async(coro: object) -> object:
    return asyncio.run(coro)


@pytest.fixture()
def auth_settings() -> Settings:
    return Settings(
        github_client_id="client-id",
        github_client_secret="client-secret",
        github_callback_url="http://localhost:8000/auth/github/callback",
        secret_key="test-secret-key",
        encryption_key=generate_encryption_key(),
    )


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_auth_service_builds_github_authorization_url(
    db_session: Session,
    auth_settings: Settings,
) -> None:
    service = AuthServiceClass(db_session, app_settings=auth_settings)

    url = service.build_authorization_url("state-123")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "github.com"
    assert parsed.path == "/login/oauth/authorize"
    assert query["client_id"] == ["client-id"]
    assert query["redirect_uri"] == ["http://localhost:8000/auth/github/callback"]
    assert query["scope"] == ["repo read:user"]
    assert query["state"] == ["state-123"]
    assert "scope=repo%20read%3Auser" in url
    assert "scope=repo+read" not in url


def test_auth_service_exchanges_code_fetches_user_and_encrypts_token(
    db_session: Session,
    auth_settings: Settings,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/login/oauth/access_token":
            body = request.content.decode("utf-8")
            assert "client_secret=client-secret" in body
            assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Fgithub%2Fcallback" in body
            return httpx.Response(200, json={"access_token": "github-token"})

        if request.url.path == "/user":
            assert request.headers["Authorization"] == "Bearer github-token"
            return httpx.Response(
                200,
                json={
                    "id": 1001,
                    "login": "octo",
                    "name": "Octo Cat",
                    "avatar_url": "https://avatars.test/octo.png",
                },
            )

        return httpx.Response(404, json={"message": "not found"})

    async def run_flow() -> User:
        async with httpx.AsyncClient(
            base_url="https://github.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            service = AuthServiceClass(
                db_session,
                app_settings=auth_settings,
                http_client=client,
            )
            return await service.authenticate_callback(code="code-123", state="state-123")

    user = run_async(run_flow())
    saved_user = db_session.scalar(select(User).where(User.github_id == 1001))

    assert isinstance(user, User)
    assert saved_user is not None
    assert saved_user.github_login == "octo"
    assert saved_user.encrypted_github_token != "github-token"
    assert (
        decrypt_token(
            saved_user.encrypted_github_token,
            encryption_key=auth_settings.encryption_key,
        )
        == "github-token"
    )
    assert [request.url.path for request in requests] == [
        "/login/oauth/access_token",
        "/user",
    ]


def test_auth_service_rejects_invalid_token_response(
    db_session: Session,
    auth_settings: Settings,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "bad_verification_code"})

    async def run_flow() -> None:
        async with httpx.AsyncClient(
            base_url="https://github.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            service = AuthServiceClass(
                db_session,
                app_settings=auth_settings,
                http_client=client,
            )
            await service.authenticate_callback(code="bad-code", state="state-123")

    with pytest.raises(AuthenticationException):
        run_async(run_flow())


def test_login_page_and_github_login_route_set_state_cookie(
    db_session: Session,
) -> None:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    login_page = client.get("/login")
    assert login_page.status_code == 200
    assert "Login with GitHub" in login_page.text

    response = client.get("/auth/github/login", follow_redirects=False)
    location = response.headers["location"]
    query = parse_qs(urlparse(location).query)

    assert response.status_code == 302
    assert urlparse(location).path == "/login/oauth/authorize"
    assert "scope=repo%20read%3Auser" in location
    assert "scope=repo+read" not in location
    assert query["redirect_uri"] == ["http://localhost:8000/auth/github/callback"]
    assert query["scope"] == ["repo read:user"]
    assert query["state"][0]
    state_cookie = response.cookies.get("git_analytics_oauth_state")
    assert state_cookie is not None
    assert query["state"] == [state_cookie]


def test_auth_routes_redirect_127_to_localhost_before_setting_cookie(
    db_session: Session,
) -> None:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, base_url="http://127.0.0.1:8000")

    login_response = client.get("/login", follow_redirects=False)
    oauth_response = client.get("/auth/github/login", follow_redirects=False)

    assert login_response.status_code == 307
    assert login_response.headers["location"] == "http://localhost:8000/login"
    assert oauth_response.status_code == 307
    assert (
        oauth_response.headers["location"]
        == "http://localhost:8000/auth/github/login"
    )
    assert oauth_response.cookies.get("git_analytics_oauth_state") is None


def test_callback_route_validates_state_and_sets_session_cookie(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_authenticate_callback(
        self: AuthServiceClass,
        *,
        code: str,
        state: str,
    ) -> User:
        assert code == "code-123"
        assert state
        user = User(
            github_id=1001,
            github_login="octo",
            encrypted_github_token="encrypted",
        )
        user.id = 42
        return user

    monkeypatch.setattr(
        AuthService,
        "authenticate_callback",
        fake_authenticate_callback,
    )
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set(
        "git_analytics_oauth_state",
        create_oauth_state_cookie("state-123"),
    )
    signed_state = client.cookies.get("git_analytics_oauth_state")

    response = client.get(
        f"/auth/github/callback?code=code-123&state={signed_state}",
        follow_redirects=False,
    )
    session_cookie = response.cookies.get("git_analytics_session")

    assert response.status_code == 302
    assert response.headers["location"] == "/repositories"
    assert session_cookie is not None
    assert parse_session_cookie(session_cookie) == 42


def test_callback_route_rejects_state_mismatch(db_session: Session) -> None:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set(
        "git_analytics_oauth_state",
        create_oauth_state_cookie("expected-state"),
    )

    response = client.get(
        "/auth/github/callback?code=code-123&state=wrong-state",
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_logout_clears_session_cookie() -> None:
    app = create_app()
    client = TestClient(app)
    client.cookies.set("git_analytics_session", "value")

    response = client.post("/auth/logout", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/login"
    assert "git_analytics_session" in response.headers["set-cookie"]




def test_repositories_page_shows_logged_in_user(db_session: Session) -> None:
    user = User(
        github_id=1001,
        github_login="octo",
        encrypted_github_token="encrypted",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.cookies.set("git_analytics_session", create_session_cookie(user.id))

    response = client.get("/repositories")

    assert response.status_code == 200
    assert "Repositories" in response.text
    assert "octo" in response.text
    assert "Đăng Xuất" in response.text
