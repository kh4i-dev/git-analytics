import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.exceptions import (
    GitHubAPIError,
    GitHubAuthFailed,
    GitHubNotFound,
    GitHubRateLimitExceeded,
    GitHubServerError,
)


class GitHubClient:
    def __init__(
        self,
        access_token: str,
        *,
        base_url: str = "https://api.github.com",
        timeout: float = 10.0,
        retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            transport=transport,
        )

    async def __aenter__(self) -> "GitHubClient":
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_rate_limit(self) -> dict[str, Any]:
        response = await self._request("GET", "/rate_limit")
        payload = response.json()
        core = payload.get("resources", {}).get("core", {})
        return {
            "limit": core.get("limit"),
            "remaining": core.get("remaining"),
            "reset_at": self._timestamp_to_iso(core.get("reset")),
            "raw": payload,
        }

    async def list_user_repositories(self) -> list[dict[str, Any]]:
        return await self._paginate(
            "/user/repos",
            params={
                "type": "owner",
                "sort": "updated",
                "direction": "desc",
            },
        )

    async def list_commits(
        self,
        owner: str,
        repo: str,
        since: datetime | str | None = None,
        sha: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if since is not None:
            params["since"] = self._format_datetime(since)
        if sha:
            params["sha"] = sha
        return await self._paginate(f"/repos/{owner}/{repo}/commits", params=params)

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "all",
        since: datetime | str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "state": state,
            "sort": "updated",
            "direction": "desc",
        }
        pull_requests = await self._paginate(f"/repos/{owner}/{repo}/pulls", params=params)
        if since is None:
            return pull_requests

        since_dt = self._parse_datetime(since)
        return [
            pull_request
            for pull_request in pull_requests
            if self._parse_datetime(pull_request["updated_at"]) >= since_dt
        ]

    async def list_issues(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "all",
        since: datetime | str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"state": state}
        if since is not None:
            params["since"] = self._format_datetime(since)
        return await self._paginate(f"/repos/{owner}/{repo}/issues", params=params)

    async def list_contributors(self, owner: str, repo: str) -> list[dict[str, Any]]:
        return await self._paginate(f"/repos/{owner}/{repo}/contributors")

    async def list_branches(self, owner: str, repo: str) -> list[dict[str, Any]]:
        return await self._paginate(f"/repos/{owner}/{repo}/branches")

    async def _paginate(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        request_params: Mapping[str, Any] | None = {"per_page": 100, **dict(params or {})}
        next_url: str | None = path

        while next_url is not None:
            response = await self._request("GET", next_url, params=request_params)
            payload = response.json()
            if not isinstance(payload, list):
                raise GitHubAPIError("Expected a list response from GitHub API.")

            items.extend(payload)
            next_url = self._next_link(response.headers.get("Link"))
            request_params = None

        return items

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> httpx.Response:
        attempts = self.retries + 1
        for attempt in range(attempts):
            try:
                response = await self._client.request(method, url, params=params)
            except httpx.TransportError as exc:
                if attempt == attempts - 1:
                    raise GitHubAPIError(
                        "Network error while calling GitHub API.",
                        details={"error": str(exc)},
                    ) from exc
                await asyncio.sleep(0.1 * (attempt + 1))
                continue

            self._handle_error_response(response)
            return response

        raise GitHubAPIError("GitHub API request failed.")

    def _handle_error_response(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return

        details = {
            "status_code": response.status_code,
            "rate_limit": self.parse_rate_limit_headers(response.headers),
        }
        message = self._error_message(response)

        if response.status_code == 401:
            raise GitHubAuthFailed(message, details=details)
        if response.status_code == 403 and self._is_rate_limited(response):
            raise GitHubRateLimitExceeded(message, details=details)
        if response.status_code == 404:
            raise GitHubNotFound(message, details=details)
        if response.status_code >= 500:
            raise GitHubServerError(message, details=details)

        raise GitHubAPIError(message, details=details)

    def parse_rate_limit_headers(self, headers: httpx.Headers) -> dict[str, Any]:
        reset_at = self._timestamp_to_iso(headers.get("x-ratelimit-reset"))
        return {
            "limit": self._to_int(headers.get("x-ratelimit-limit")),
            "remaining": self._to_int(headers.get("x-ratelimit-remaining")),
            "used": self._to_int(headers.get("x-ratelimit-used")),
            "resource": headers.get("x-ratelimit-resource"),
            "reset_at": reset_at,
        }

    def _is_rate_limited(self, response: httpx.Response) -> bool:
        remaining = self._to_int(response.headers.get("x-ratelimit-remaining"))
        if remaining == 0:
            return True

        message = self._error_message(response).lower()
        return "rate limit" in message

    def _error_message(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text or "GitHub API request failed."

        message = payload.get("message")
        if isinstance(message, str) and message:
            return message
        return "GitHub API request failed."

    def _next_link(self, link_header: str | None) -> str | None:
        if not link_header:
            return None

        links = link_header.split(",")
        for link in links:
            section = link.strip()
            if 'rel="next"' not in section:
                continue
            url_part = section.split(";", maxsplit=1)[0].strip()
            if url_part.startswith("<") and url_part.endswith(">"):
                return url_part[1:-1]
        return None

    def _format_datetime(self, value: datetime | str) -> str:
        if isinstance(value, str):
            return value
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

    def _parse_datetime(self, value: datetime | str) -> datetime:
        if isinstance(value, datetime):
            parsed = value
        else:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _timestamp_to_iso(self, value: int | str | None) -> str | None:
        timestamp = self._to_int(value)
        if timestamp is None:
            return None
        return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()

    def _to_int(self, value: int | str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
