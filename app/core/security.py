from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.exceptions import AuthenticationException


def generate_encryption_key() -> str:
    return Fernet.generate_key().decode("utf-8")


def encrypt_token(token: str, encryption_key: str | None = None) -> str:
    key = encryption_key or settings.encryption_key
    if not key:
        raise AuthenticationException("ENCRYPTION_KEY is not configured.")
    return Fernet(key.encode("utf-8")).encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str, encryption_key: str | None = None) -> str:
    key = encryption_key or settings.encryption_key
    if not key:
        raise AuthenticationException("ENCRYPTION_KEY is not configured.")
    try:
        return Fernet(key.encode("utf-8")).decrypt(
            encrypted_token.encode("utf-8"),
        ).decode("utf-8")
    except InvalidToken as exc:
        raise AuthenticationException("Stored GitHub token cannot be decrypted.") from exc
