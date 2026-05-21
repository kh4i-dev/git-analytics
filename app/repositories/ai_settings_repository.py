from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.models.ai_provider_setting import AiProviderSetting
from app.repositories.base import BaseRepository


class AiSettingsRepository(BaseRepository[AiProviderSetting]):
    def get_settings_for_user(self, user_id: int) -> list[AiProviderSetting]:
        try:
            return list(
                self.db.scalars(
                    select(AiProviderSetting)
                    .where(AiProviderSetting.user_id == user_id)
                    .order_by(AiProviderSetting.mode, AiProviderSetting.provider),
                ),
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def list_provider_keys(self, user_id: int) -> list[AiProviderSetting]:
        try:
            return list(
                self.db.scalars(
                    select(AiProviderSetting)
                    .where(
                        AiProviderSetting.user_id == user_id,
                        AiProviderSetting.mode == "byok",
                    )
                    .order_by(AiProviderSetting.provider),
                ),
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_default_for_user(self, user_id: int) -> AiProviderSetting | None:
        try:
            return self.db.scalar(
                select(AiProviderSetting)
                .where(
                    AiProviderSetting.user_id == user_id,
                    AiProviderSetting.is_default.is_(True),
                )
                .order_by(AiProviderSetting.updated_at.desc()),
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_by_user_mode_provider(
        self,
        user_id: int,
        mode: str,
        provider: str,
    ) -> AiProviderSetting | None:
        try:
            return self.db.scalar(
                select(AiProviderSetting).where(
                    AiProviderSetting.user_id == user_id,
                    AiProviderSetting.mode == mode,
                    AiProviderSetting.provider == provider,
                ),
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def upsert_byok_key(
        self,
        user_id: int,
        provider: str,
        encrypted_api_key: str,
    ) -> AiProviderSetting:
        setting = self.get_by_user_mode_provider(user_id, "byok", provider)
        data = {"encrypted_api_key": encrypted_api_key}
        if setting is not None:
            return self._apply_updates(setting, data)
        setting = AiProviderSetting(
            user_id=user_id,
            mode="byok",
            provider=provider,
            encrypted_api_key=encrypted_api_key,
            is_default=False,
        )
        self.db.add(setting)
        self._flush()
        return setting

    def delete_provider_key(self, user_id: int, provider: str) -> None:
        try:
            self.db.execute(
                delete(AiProviderSetting).where(
                    AiProviderSetting.user_id == user_id,
                    AiProviderSetting.mode == "byok",
                    AiProviderSetting.provider == provider,
                ),
            )
            self._flush()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def delete_all_byok_keys(self, user_id: int) -> None:
        try:
            self.db.execute(
                delete(AiProviderSetting).where(
                    AiProviderSetting.user_id == user_id,
                    AiProviderSetting.mode == "byok",
                ),
            )
            self._flush()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def set_default_provider(
        self,
        user_id: int,
        provider: str,
        mode: str | None = None,
    ) -> AiProviderSetting | None:
        target_mode = mode or "byok"
        setting = self.get_by_user_mode_provider(user_id, target_mode, provider)
        if setting is None:
            return None
        try:
            self.db.execute(
                update(AiProviderSetting)
                .where(AiProviderSetting.user_id == user_id)
                .values(is_default=False),
            )
            setting.is_default = True
            self._flush()
            return setting
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def set_ai_mode(
        self,
        user_id: int,
        mode: str,
        provider: str,
    ) -> AiProviderSetting | None:
        if mode == "cloud":
            setting = self.get_by_user_mode_provider(user_id, "cloud", provider)
            if setting is None:
                setting = AiProviderSetting(
                    user_id=user_id,
                    mode="cloud",
                    provider=provider,
                    encrypted_api_key=None,
                    is_default=False,
                )
                self.db.add(setting)
                self._flush()
            return self.set_default_provider(user_id, provider, mode="cloud")
        return self.set_default_provider(user_id, provider, mode="byok")
