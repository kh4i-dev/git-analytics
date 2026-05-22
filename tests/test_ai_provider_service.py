import asyncio
import json
from collections.abc import Generator

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.config import Settings
from app.core.exceptions import AIRateLimitException
from app.db.base import Base
from app.models.ai_usage_event import AiUsageEvent
from app.repositories import UserRepository
from app.services.ai_provider_service import AiProviderGateway, AiToolService
from app.services.ai_settings_service import AiSettingsService


def run_async(coro: object) -> object:
    return asyncio.run(coro)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session)
    session = factory()
    try:
        yield session
    finally:
        session.close()


def _make_user(db: Session):
    user = UserRepository(db).create(
        {
            "github_id": 2026,
            "github_login": "preview",
            "encrypted_github_token": "encrypted",
        }
    )
    db.commit()
    return user


def test_openai_compatible_cloud_gateway_uses_server_config() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "fix(ai): route provider calls"}}],
                "usage": {"total_tokens": 9},
            },
        )

    app_settings = Settings(
        openai_compatible_base_url="https://openclaw.test/v1",
        openai_compatible_model="gateway-model",
    )

    async def execute() -> object:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            gateway = AiProviderGateway(app_settings=app_settings, http_client=client)
            return await gateway.complete(
                mode="cloud",
                provider="openai",
                api_key="cloud-secret",
                system_prompt="Return one line.",
                user_prompt="diff",
            )

    completion = run_async(execute())

    assert completion.text == "fix(ai): route provider calls"
    assert completion.usage_units == 9
    assert requests[0].url == "https://openclaw.test/v1/chat/completions"
    assert requests[0].headers["Authorization"] == "Bearer cloud-secret"
    assert json.loads(requests[0].content)["model"] == "gateway-model"


def test_cloud_tool_records_usage_and_enforces_preview_limit(
    db_session: Session,
) -> None:
    user = _make_user(db_session)
    app_settings = Settings(
        openai_compatible_base_url="https://openclaw.test/v1",
        openai_compatible_api_key="cloud-key",
        cloud_ai_preview_daily_limit=1,
    )
    AiSettingsService(db_session, app_settings=app_settings).update_settings(
        user.id,
        {"mode": "cloud", "default_provider": "openai"},
    )

    class FakeGateway:
        async def complete(self, **_kwargs):
            from app.services.ai_provider_service import AiCompletion

            return AiCompletion("feat(ai): use cloud preview", usage_units=13)

    tool = AiToolService(
        db_session,
        app_settings=app_settings,
        gateway=FakeGateway(),
    )

    first = run_async(
        tool.generate_commit_message(user_id=user.id, diff="diff --git a/a.py b/a.py")
    )
    with pytest.raises(AIRateLimitException):
        run_async(
            tool.generate_commit_message(
                user_id=user.id,
                diff="diff --git a/b.py b/b.py",
            )
        )

    events = db_session.scalars(select(AiUsageEvent)).all()
    assert first["message"] == "feat(ai): use cloud preview"
    assert len(events) == 1
    assert events[0].usage_units == 13
    assert events[0].operation == "commit_message"
