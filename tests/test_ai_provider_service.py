import asyncio
import json
from collections.abc import Generator

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.config import Settings
from app.core.exceptions import AIRateLimitException, ValidationException
from app.db.base import Base
from app.models.ai_usage_event import AiUsageEvent
from app.repositories import UserRepository, RepositoryRepository
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


def test_git_diff_validation(db_session: Session) -> None:
    user = _make_user(db_session)
    tool = AiToolService(db_session)
    with pytest.raises(ValidationException) as exc:
        run_async(tool.generate_commit_message(user_id=user.id, diff="not a git diff"))
    assert "Invalid git diff format" in str(exc.value)


def test_inject_metadata_in_responses(db_session: Session) -> None:
    user = _make_user(db_session)
    app_settings = Settings(
        openai_compatible_base_url="https://openclaw.test/v1",
        openai_compatible_api_key="cloud-key",
    )
    AiSettingsService(db_session, app_settings=app_settings).update_settings(
        user.id,
        {"mode": "cloud", "default_provider": "openai"},
    )

    class FakeGateway:
        async def complete(self, **_kwargs):
            from app.services.ai_provider_service import AiCompletion

            return AiCompletion("feat(ai): correct active provider", usage_units=10)

    tool = AiToolService(db_session, app_settings=app_settings, gateway=FakeGateway())
    res = run_async(tool.generate_commit_message(user_id=user.id, diff="diff --git a/a.py b/a.py"))
    assert "metadata" in res
    assert res["metadata"]["mode"] == "cloud"
    assert res["metadata"]["provider"] == "openai"
    assert res["metadata"]["source"] == "Cloud AI · OpenClaw"


def test_post_json_raises_validation_exception_on_401_403() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    async def execute() -> object:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            gateway = AiProviderGateway(http_client=client)
            return await gateway._post_json(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": "Bearer bad-key"},
                json_body={},
            )

    with pytest.raises(ValidationException) as exc:
        run_async(execute())
    assert "Invalid API key configured for the AI provider" in str(exc.value)


def test_nvidia_completion_uses_correct_endpoint() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "fix(nvidia): complete NIM integration"}}],
                "usage": {"total_tokens": 12},
            },
        )

    app_settings = Settings(
        nvidia_api_key="nvidia-secret",
        nvidia_model="custom-nvidia-nim-model",
    )

    async def execute() -> object:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            gateway = AiProviderGateway(app_settings=app_settings, http_client=client)
            return await gateway.complete(
                mode="byok",
                provider="nvidia",
                api_key="nvidia-secret",
                system_prompt="System Prompt",
                user_prompt="User Prompt",
            )

    completion = run_async(execute())

    assert completion.text == "fix(nvidia): complete NIM integration"
    assert completion.usage_units == 12
    assert requests[0].url == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert requests[0].headers["Authorization"] == "Bearer nvidia-secret"
    assert json.loads(requests[0].content)["model"] == "custom-nvidia-nim-model"


def test_repo_scoped_retrieval_isolation(db_session: Session) -> None:
    user = _make_user(db_session)
    
    # 1. Create a foreign repository that is NOT indexed (BAITAP_HQTCSDL)
    foreign_repo = RepositoryRepository(db_session).create({
        "user_id": user.id,
        "github_repo_id": 9002,
        "owner": "kh4i-dev",
        "name": "BAITAP_HQTCSDL",
        "full_name": "kh4i-dev/BAITAP_HQTCSDL",
        "html_url": "https://github.com/kh4i-dev/BAITAP_HQTCSDL",
        "default_branch": "main",
        "last_sync_status": "success",
    })
    
    # 2. Create the indexed local repository (git-analytics)
    local_repo = RepositoryRepository(db_session).create({
        "user_id": user.id,
        "github_repo_id": 9003,
        "owner": "kh4i-dev",
        "name": "git-analytics",
        "full_name": "kh4i-dev/git-analytics",
        "html_url": "https://github.com/kh4i-dev/git-analytics",
        "default_branch": "main",
        "last_sync_status": "success",
    })
    db_session.commit()
    
    # Mock settings
    app_settings = Settings(
        openai_compatible_base_url="https://openclaw.test/v1",
        openai_compatible_api_key="cloud-key",
    )
    AiSettingsService(db_session, app_settings=app_settings).update_settings(
        user.id,
        {"mode": "cloud", "default_provider": "openai"},
    )
    
    class FakeGateway:
        async def complete(self, **_kwargs):
            from app.services.ai_provider_service import AiCompletion
            return AiCompletion("Mock response text.", usage_units=5)
            
    tool = AiToolService(db_session, app_settings=app_settings, gateway=FakeGateway())
    
    # Querying the foreign repository
    res_foreign = run_async(
        tool.answer_question(
            user_id=user.id,
            question="Tell me about auth flow or sync pipeline",
            repo_id=foreign_repo.id,
            branch="main"
        )
    )
    
    # Querying a foreign repository must return empty index message
    assert res_foreign["answer"] == "No indexed source files available for this repository."
    assert res_foreign["context_metadata"]["repository_source"] == "Empty/Non-indexed"
    assert res_foreign["context_metadata"]["retrieved_chunk_count"] == 0
    assert len(res_foreign["context_metadata"]["retrieved_files"]) == 0


def test_empty_repo_no_global_fallback(db_session: Session) -> None:
    user = _make_user(db_session)
    
    # Create empty repo
    empty_repo = RepositoryRepository(db_session).create({
        "user_id": user.id,
        "github_repo_id": 9004,
        "owner": "kh4i-dev",
        "name": "empty-project",
        "full_name": "kh4i-dev/empty-project",
        "html_url": "https://github.com/kh4i-dev/empty-project",
        "default_branch": "main",
        "last_sync_status": "success",
    })
    db_session.commit()
    
    app_settings = Settings()
    tool = AiToolService(db_session, app_settings=app_settings)
    
    res = run_async(
        tool.answer_question(
            user_id=user.id,
            question="Give me the contents of auth_service.py or sync_service.py",
            repo_id=empty_repo.id,
            branch="main"
        )
    )
    
    # Assert zero leakage
    assert res["answer"] == "No indexed source files available for this repository."
    assert res["context_metadata"]["repository_source"] == "Empty/Non-indexed"
    assert len(res["context_metadata"]["retrieved_files"]) == 0


def test_context_cache_invalidation(db_session: Session) -> None:
    user = _make_user(db_session)
    
    # Create indexed local repository (git-analytics)
    local_repo = RepositoryRepository(db_session).create({
        "user_id": user.id,
        "github_repo_id": 9005,
        "owner": "kh4i-dev",
        "name": "git-analytics",
        "full_name": "kh4i-dev/git-analytics",
        "html_url": "https://github.com/kh4i-dev/git-analytics",
        "default_branch": "main",
        "last_sync_status": "success",
    })
    db_session.commit()
    
    app_settings = Settings(
        openai_compatible_base_url="https://openclaw.test/v1",
        openai_compatible_api_key="cloud-key",
    )
    AiSettingsService(db_session, app_settings=app_settings).update_settings(
        user.id,
        {"mode": "cloud", "default_provider": "openai"},
    )
    
    class FakeGateway:
        async def complete(self, **_kwargs):
            from app.services.ai_provider_service import AiCompletion
            return AiCompletion("Mock answers.", usage_units=2)
            
    tool = AiToolService(db_session, app_settings=app_settings, gateway=FakeGateway())
    
    # We ask a question that triggers a cache entry
    from app.services.ai_provider_service import _assistant_cache
    
    cache_key = f"repo_assistant:{local_repo.id}:main"
    if cache_key in _assistant_cache:
        del _assistant_cache[cache_key]
        
    res = run_async(
        tool.answer_question(
            user_id=user.id,
            question="Tell me about sync worker pipeline",
            repo_id=local_repo.id,
            branch="main"
        )
    )
    
    # Cache key must exist now
    assert cache_key in _assistant_cache
    assert _assistant_cache[cache_key]["repository_source"] == "Local Workspace"
    
    # Clear context cache
    tool.clear_context_cache(repo_id=local_repo.id, branch="main")
    
    # Cache key must be deleted
    assert cache_key not in _assistant_cache


def test_get_repository_index_status(db_session: Session) -> None:
    user = _make_user(db_session)
    from app.repositories import RepositoryRepository
    from datetime import datetime, timezone
    
    synced_at = datetime.now(timezone.utc)
    local_repo = RepositoryRepository(db_session).create({
        "user_id": user.id,
        "github_repo_id": 11001,
        "owner": "kh4i-dev",
        "name": "git-analytics",
        "full_name": "kh4i-dev/git-analytics",
        "html_url": "https://github.com/kh4i-dev/git-analytics",
        "default_branch": "main",
        "last_sync_status": "success",
        "last_synced_at": synced_at,
    })
    
    failed_repo = RepositoryRepository(db_session).create({
        "user_id": user.id,
        "github_repo_id": 11002,
        "owner": "kh4i-dev",
        "name": "git-analytics",
        "full_name": "kh4i-dev/git-analytics",
        "html_url": "https://github.com/kh4i-dev/git-analytics",
        "default_branch": "main",
        "last_sync_status": "failed",
        "last_synced_at": synced_at,
    })
    
    foreign_repo = RepositoryRepository(db_session).create({
        "user_id": user.id,
        "github_repo_id": 11003,
        "owner": "kh4i-dev",
        "name": "foreign-repo",
        "full_name": "kh4i-dev/foreign-repo",
        "html_url": "https://github.com/kh4i-dev/foreign-repo",
        "default_branch": "main",
        "last_sync_status": "success",
        "last_synced_at": synced_at,
    })
    
    db_session.commit()
    
    tool = AiToolService(db_session)
    
    # Test valid/active repo
    status_local = tool.get_repository_index_status(local_repo.id)
    assert status_local["has_context"] is True
    assert status_local["file_count"] > 0
    assert status_local["chunk_count"] > 0
    assert status_local["last_indexed_at"] is not None
    
    # Test failed sync status
    status_failed = tool.get_repository_index_status(failed_repo.id)
    assert status_failed["has_context"] is False
    assert status_failed["file_count"] == 0
    assert status_failed["chunk_count"] == 0
    assert status_failed["last_indexed_at"] is None
    
    # Test cancelled sync status using mock patching to avoid DB CheckConstraint and autoflush
    from unittest.mock import patch, MagicMock
    mock_repo = MagicMock()
    mock_repo.id = 99994
    mock_repo.name = "git-analytics"
    mock_repo.full_name = "kh4i-dev/git-analytics"
    mock_repo.last_sync_status = "cancelled"
    mock_repo.last_synced_at = synced_at
    
    with patch.object(RepositoryRepository, "get_by_id", return_value=mock_repo):
        status_cancelled = tool.get_repository_index_status(mock_repo.id)
        assert status_cancelled["has_context"] is False
        assert status_cancelled["file_count"] == 0
        assert status_cancelled["chunk_count"] == 0
        assert status_cancelled["last_indexed_at"] is None
    
    # Test foreign repo
    status_foreign = tool.get_repository_index_status(foreign_repo.id)
    assert status_foreign["has_context"] is False
    assert status_foreign["file_count"] == 0
    assert status_foreign["chunk_count"] == 0
    assert status_foreign["last_indexed_at"] is None
    
    # Test non-existent repo id
    status_none = tool.get_repository_index_status(99999)
    assert status_none["has_context"] is False
    assert status_none["file_count"] == 0
    assert status_none["chunk_count"] == 0
    assert status_none["last_indexed_at"] is None


def test_get_repository_index_status_empty(db_session: Session) -> None:
    from unittest.mock import patch
    user = _make_user(db_session)
    from app.repositories import RepositoryRepository
    from datetime import datetime, timezone
    
    synced_at = datetime.now(timezone.utc)
    local_repo = RepositoryRepository(db_session).create({
        "user_id": user.id,
        "github_repo_id": 11005,
        "owner": "kh4i-dev",
        "name": "git-analytics",
        "full_name": "kh4i-dev/git-analytics",
        "html_url": "https://github.com/kh4i-dev/git-analytics",
        "default_branch": "main",
        "last_sync_status": "success",
        "last_synced_at": synced_at,
    })
    db_session.commit()
    
    tool = AiToolService(db_session)
    with patch("os.walk") as mock_walk:
        mock_walk.return_value = [(".", [], ["logo.png", "README.md"])]
        status = tool.get_repository_index_status(local_repo.id)
        assert status["indexing_status"] == "empty"
        assert status["has_context"] is False
        assert status["file_count"] == 0
        assert status["chunk_count"] == 0
        assert status["last_indexed_at"] is None

