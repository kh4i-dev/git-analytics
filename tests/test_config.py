import pytest

from app.core.config import Settings
from app.core.security import generate_encryption_key


def test_production_settings_reject_unsafe_secret_defaults() -> None:
    app_settings = Settings(
        environment="production",
        app_env="production",
        debug=True,
        secret_key="change-this-secret-key",
        encryption_key=None,
    )

    with pytest.raises(RuntimeError) as exc_info:
        app_settings.validate_runtime_security()

    assert "DEBUG" in str(exc_info.value)
    assert "SECRET_KEY" in str(exc_info.value)
    assert "ENCRYPTION_KEY" in str(exc_info.value)


def test_production_settings_allow_explicit_security_values() -> None:
    app_settings = Settings(
        environment="production",
        app_env="production",
        debug=False,
        secret_key="preview-signing-key-from-secret-manager",
        encryption_key=generate_encryption_key(),
    )

    app_settings.validate_runtime_security()
