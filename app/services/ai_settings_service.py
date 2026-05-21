from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.exceptions import ValidationException
from app.core.security import decrypt_token, encrypt_token
from app.repositories.ai_settings_repository import AiSettingsRepository


AI_MODES = {"byok", "cloud"}
AI_PROVIDERS = ("openai", "gemini", "claude")


class AiSettingsService:
    def __init__(
        self,
        db: Session,
        *,
        app_settings: Settings = settings,
    ) -> None:
        self.db = db
        self.settings = app_settings
        self.repo = AiSettingsRepository(db)

    def get_settings(self, user_id: int) -> dict[str, Any]:
        rows = self.repo.get_settings_for_user(user_id)
        default_row = next((row for row in rows if row.is_default), None)
        byok_rows = {row.provider: row for row in rows if row.mode == "byok"}
        mode = default_row.mode if default_row is not None else "byok"
        default_provider = (
            default_row.provider
            if default_row is not None
            else self._first_provider_with_key(byok_rows) or "openai"
        )
        cloud_providers = self._cloud_providers()

        return {
            "mode": self._validate_mode(mode),
            "default_provider": self._validate_provider(default_provider),
            "providers": [
                {
                    "provider": provider,
                    "has_key": provider in byok_rows,
                    "masked_key": "********" if provider in byok_rows else None,
                    "cloud_available": provider in cloud_providers,
                }
                for provider in AI_PROVIDERS
            ],
            "cloud_available": bool(cloud_providers),
            "cloud_preview": True,
        }

    def update_settings(self, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        mode = self._validate_mode(str(payload.get("mode") or "byok"))
        provider = self._validate_provider(
            str(payload.get("default_provider") or payload.get("provider") or "openai"),
        )
        keys = payload.get("keys") or {}
        if not isinstance(keys, dict):
            raise ValidationException("keys must be an object.")

        if mode == "byok":
            for raw_provider, raw_key in keys.items():
                key_provider = self._validate_provider(str(raw_provider))
                api_key = str(raw_key or "").strip()
                if api_key:
                    self.repo.upsert_byok_key(
                        user_id,
                        key_provider,
                        encrypt_token(api_key),
                    )
            if self.repo.get_by_user_mode_provider(user_id, "byok", provider) is None:
                raise ValidationException("Default BYOK provider requires a saved API key.")
            self.repo.set_ai_mode(user_id, "byok", provider)
        else:
            if provider not in self._cloud_providers():
                raise ValidationException("Cloud AI is not configured for this provider.")
            self.repo.set_ai_mode(user_id, "cloud", provider)

        self.db.commit()
        return self.get_settings(user_id)

    def delete_provider_key(self, user_id: int, provider: str) -> dict[str, Any]:
        provider = self._validate_provider(provider)
        self.repo.delete_provider_key(user_id, provider)
        self.db.commit()
        return self.get_settings(user_id)

    def delete_all_byok_keys(self, user_id: int) -> dict[str, Any]:
        self.repo.delete_all_byok_keys(user_id)
        self.db.commit()
        return self.get_settings(user_id)

    def get_execution_api_key(self, user_id: int) -> tuple[str, str]:
        current = self.get_settings(user_id)
        mode = current["mode"]
        provider = current["default_provider"]
        if mode == "cloud":
            key = self._cloud_key(provider)
            if not key:
                raise ValidationException("Cloud AI is not configured for this provider.")
            return provider, key

        row = self.repo.get_by_user_mode_provider(user_id, "byok", provider)
        if row is None or not row.encrypted_api_key:
            raise ValidationException("Default BYOK provider requires a saved API key.")
        return provider, decrypt_token(row.encrypted_api_key)

    def _validate_mode(self, mode: str) -> str:
        if mode not in AI_MODES:
            raise ValidationException("Invalid AI mode.")
        return mode

    def _validate_provider(self, provider: str) -> str:
        if provider not in AI_PROVIDERS:
            raise ValidationException("Invalid AI provider.")
        return provider

    def _cloud_key(self, provider: str) -> str | None:
        return {
            "openai": self.settings.openai_api_key,
            "gemini": self.settings.gemini_api_key,
            "claude": self.settings.claude_api_key,
        }.get(provider)

    def _cloud_providers(self) -> set[str]:
        return {provider for provider in AI_PROVIDERS if self._cloud_key(provider)}

    def _first_provider_with_key(self, byok_rows: dict[str, object]) -> str | None:
        for provider in AI_PROVIDERS:
            if provider in byok_rows:
                return provider
        return None
