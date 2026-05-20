import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypeVar

import httpx
import pytest

from app.clients.github_client import GitHubClient
from app.core.exceptions import (
    GitHubAPIError,
    GitHubAuthFailed,
    GitHubNotFound,
    GitHubRateLimitExceeded,
    GitHubServerError,
)

T = TypeVar("T")


def run_async(coro: Any) -> T:
    return asyncio.run(coro)


def make_client(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    retries: int = 0,
) -> GitHubClient:
    return GitHubClient(
        "secret-token",
        base_url="https://api.github.test",
        retries=retries,
        transport=httpx.MockTransport(handler),
    )


def test_list_user_repositories_sends_auth_and_paginates() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["Authorization"] == "Bearer secret-token"

        if len(requests) == 1:
            assert request.url.params["per_page"] == "100"
            return httpx.Response(
                200,
                json=[{"id": 1}],
                headers={
                    "Link": '<https://api.github.test/user/repos?page=2>; rel="next"'
                },
            )
        return httpx.Response(200, json=[{"id": 2}])

    client = make_client(handler)
    try:
        repositories = run_async(client.list_user_repositories())
    finally:
        run_async(client.aclose())

    assert repositories == [{"id": 1}, {"id": 2}]
    assert len(requests) == 2
    assert requests[0].url.path == "/user/repos"
    assert requests[1].url.params["page"] == "2"


def test_get_rate_limit_parses_core_resource() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"resources": {"core": {"limit": 5000, "remaining": 4999, "reset": 1}}},
        )

    client = make_client(handler)
    try:
        rate_limit = run_async(client.get_rate_limit())
    finally:
        run_async(client.aclose())

    assert rate_limit["limit"] == 5000
    assert rate_limit["remaining"] == 4999
    assert rate_limit["reset_at"] == "1970-01-01T00:00:01+00:00"


def test_list_commits_uses_since_and_list_endpoint_only() -> None:
    since = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/demo/repo/commits"
        assert request.url.params["since"] == "2026-05-20T12:00:00Z"
        return httpx.Response(200, json=[{"sha": "abc123"}])

    client = make_client(handler)
    try:
        commits = run_async(client.list_commits("demo", "repo", since=since))
    finally:
        run_async(client.aclose())

    assert commits == [{"sha": "abc123"}]


def test_list_pull_requests_filters_since_client_side() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/demo/repo/pulls"
        assert "since" not in request.url.params
        assert request.url.params["state"] == "all"
        return httpx.Response(
            200,
            json=[
                {"number": 1, "updated_at": "2026-05-19T00:00:00Z"},
                {"number": 2, "updated_at": "2026-05-21T00:00:00Z"},
            ],
        )

    client = make_client(handler)
    try:
        pull_requests = run_async(
            client.list_pull_requests(
                "demo",
                "repo",
                since="2026-05-20T00:00:00Z",
            )
        )
    finally:
        run_async(client.aclose())

    assert pull_requests == [{"number": 2, "updated_at": "2026-05-21T00:00:00Z"}]


def test_list_issues_uses_since_and_keeps_labels() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/demo/repo/issues"
        assert request.url.params["since"] == "2026-05-20T00:00:00Z"
        return httpx.Response(
            200,
            json=[{"number": 1, "labels": [{"name": "bug", "color": "red"}]}],
        )

    client = make_client(handler)
    try:
        issues = run_async(
            client.list_issues("demo", "repo", since="2026-05-20T00:00:00Z")
        )
    finally:
        run_async(client.aclose())

    assert issues[0]["labels"] == [{"name": "bug", "color": "red"}]


def test_list_contributors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/demo/repo/contributors"
        return httpx.Response(200, json=[{"login": "demo"}])

    client = make_client(handler)
    try:
        contributors = run_async(client.list_contributors("demo", "repo"))
    finally:
        run_async(client.aclose())

    assert contributors == [{"login": "demo"}]


@pytest.mark.parametrize(
    ("status_code", "headers", "exception_type"),
    [
        (401, {}, GitHubAuthFailed),
        (403, {"x-ratelimit-remaining": "0"}, GitHubRateLimitExceeded),
        (404, {}, GitHubNotFound),
        (500, {}, GitHubServerError),
        (422, {}, GitHubAPIError),
    ],
)
def test_error_mapping(
    status_code: int,
    headers: dict[str, str],
    exception_type: type[Exception],
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            headers=headers,
            json={"message": "GitHub error"},
        )

    client = make_client(handler)
    try:
        with pytest.raises(exception_type):
            run_async(client.list_contributors("demo", "repo"))
    finally:
        run_async(client.aclose())


def test_network_error_retries_then_succeeds() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("temporary failure", request=request)
        return httpx.Response(200, json=[{"login": "demo"}])

    client = make_client(handler, retries=1)
    try:
        contributors = run_async(client.list_contributors("demo", "repo"))
    finally:
        run_async(client.aclose())

    assert contributors == [{"login": "demo"}]
    assert attempts == 2


def test_rate_limit_403_is_not_retried() -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            403,
            headers={
                "x-ratelimit-limit": "5000",
                "x-ratelimit-remaining": "0",
                "x-ratelimit-reset": "1",
            },
            json={"message": "API rate limit exceeded"},
        )

    client = make_client(handler, retries=3)
    try:
        with pytest.raises(GitHubRateLimitExceeded) as exc_info:
            run_async(client.list_contributors("demo", "repo"))
    finally:
        run_async(client.aclose())

    assert attempts == 1
    assert exc_info.value.details["rate_limit"]["remaining"] == 0
    assert exc_info.value.details["rate_limit"]["reset_at"] == "1970-01-01T00:00:01+00:00"
