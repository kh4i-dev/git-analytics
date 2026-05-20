from collections.abc import Mapping
from datetime import UTC, datetime
import logging
from typing import Any
from urllib.parse import quote, urlencode

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.exceptions import AuthenticationException
from app.core.security import encrypt_token
from app.models.user import User
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    github_authorize_url = "https://github.com/login/oauth/authorize"
    github_token_url = "https://github.com/login/oauth/access_token"
    github_user_url = "https://api.github.com/user"

    def __init__(
        self,
        db: Session,
        *,
        app_settings: Settings = settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.db = db
        self.settings = app_settings
        self.http_client = http_client
        self.user_repo = UserRepository(db)

    def build_authorization_url(self, state: str) -> str:
        self._require_github_config()
        params = {
            "client_id": self.settings.github_client_id,
            "redirect_uri": self.settings.github_callback_url,
            "scope": "repo read:user",
            "state": state,
        }
        query = urlencode(params, quote_via=quote)
        authorization_url = f"{self.github_authorize_url}?{query}"
        safe_query = urlencode({**params, "state": "<redacted>"}, quote_via=quote)
        logger.debug(
            "GitHub OAuth authorize URL: %s?%s",
            self.github_authorize_url,
            safe_query,
        )
        return authorization_url

    async def authenticate_callback(self, *, code: str, state: str) -> User:
        if not code:
            raise AuthenticationException("GitHub OAuth callback is missing code.")
        if not state:
            raise AuthenticationException("GitHub OAuth callback is missing state.")

        try:
            access_token = await self._exchange_code_for_token(code)
            profile = await self._fetch_github_user(access_token)
            user = self._upsert_user(profile, access_token)
            self.db.commit()
            return user
        except Exception:
            self.db.rollback()
            raise

    async def _exchange_code_for_token(self, code: str) -> str:
        self._require_github_config()
        payload = {
            "client_id": self.settings.github_client_id,
            "client_secret": self.settings.github_client_secret,
            "code": code,
            "redirect_uri": self.settings.github_callback_url,
        }
        response = await self._post_token(payload)
        if response.status_code >= 400:
            raise AuthenticationException("GitHub OAuth token exchange failed.")

        body = response.json()
        error = body.get("error")
        if error:
            raise AuthenticationException("GitHub OAuth token exchange failed.")

        access_token = body.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise AuthenticationException("GitHub OAuth token response is invalid.")
        return access_token

    async def _fetch_github_user(self, access_token: str) -> dict[str, Any]:
        response = await self._get_user(access_token)
        if response.status_code == 401:
            raise AuthenticationException("GitHub access token is invalid.")
        if response.status_code >= 400:
            raise AuthenticationException("GitHub user profile request failed.")

        profile = response.json()
        if not isinstance(profile.get("id"), int) or not isinstance(
            profile.get("login"),
            str,
        ):
            raise AuthenticationException("GitHub user profile response is invalid.")
        return profile

    def _upsert_user(self, profile: Mapping[str, Any], access_token: str) -> User:
        encrypted_token = encrypt_token(
            access_token,
            encryption_key=self.settings.encryption_key,
        )
        return self.user_repo.upsert_by_github_id(
            {
                "github_id": profile["id"],
                "github_login": profile["login"],
                "name": profile.get("name"),
                "avatar_url": profile.get("avatar_url"),
                "encrypted_github_token": encrypted_token,
                "last_login_at": datetime.now(UTC),
            }
        )

    async def _post_token(self, payload: dict[str, Any]) -> httpx.Response:
        if self.http_client is not None:
            return await self.http_client.post(
                self.github_token_url,
                data=payload,
                headers={"Accept": "application/json"},
            )

        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                self.github_token_url,
                data=payload,
                headers={"Accept": "application/json"},
            )

    async def _get_user(self, access_token: str) -> httpx.Response:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.http_client is not None:
            return await self.http_client.get(self.github_user_url, headers=headers)

        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(self.github_user_url, headers=headers)

    def _require_github_config(self) -> None:
        if not self.settings.github_client_id or not self.settings.github_client_secret:
            raise AuthenticationException("GitHub OAuth is not configured.")
