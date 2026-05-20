import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.core.config import settings
from app.core.exceptions import AuthenticationException


def sign_payload(payload: dict[str, Any], *, max_age_seconds: int | None = None) -> str:
    body = dict(payload)
    body["iat"] = int(time.time())
    if max_age_seconds is not None:
        body["exp"] = body["iat"] + max_age_seconds

    encoded_body = _b64encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    signature = _signature(encoded_body)
    return f"{encoded_body}.{signature}"


def unsign_payload(value: str) -> dict[str, Any]:
    try:
        encoded_body, signature = value.split(".", maxsplit=1)
    except ValueError as exc:
        raise AuthenticationException("Invalid signed cookie.") from exc

    expected_signature = _signature(encoded_body)
    if not hmac.compare_digest(signature, expected_signature):
        raise AuthenticationException("Invalid signed cookie signature.")

    try:
        payload = json.loads(_b64decode(encoded_body))
    except (ValueError, json.JSONDecodeError) as exc:
        raise AuthenticationException("Invalid signed cookie payload.") from exc

    expires_at = payload.get("exp")
    if isinstance(expires_at, int) and expires_at < int(time.time()):
        raise AuthenticationException("Signed cookie expired.")

    return payload


def create_session_cookie(user_id: int) -> str:
    return sign_payload({"user_id": user_id}, max_age_seconds=60 * 60 * 24 * 7)


def parse_session_cookie(value: str) -> int:
    payload = unsign_payload(value)
    user_id = payload.get("user_id")
    if not isinstance(user_id, int):
        raise AuthenticationException("Session cookie is missing user_id.")
    return user_id


def create_oauth_state_cookie(state: str) -> str:
    return sign_payload({"state": state}, max_age_seconds=60 * 10)


def parse_oauth_state_cookie(value: str) -> str:
    payload = unsign_payload(value)
    state = payload.get("state")
    if not isinstance(state, str) or not state:
        raise AuthenticationException("OAuth state cookie is invalid.")
    return state


def _signature(encoded_body: str) -> str:
    digest = hmac.new(
        settings.secret_key.encode("utf-8"),
        encoded_body.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _b64encode(digest)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
