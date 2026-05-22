from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationException
from app.core.session import parse_session_cookie
from app.models.user import User
from app.repositories import UserRepository


def get_optional_user(request: Request, db: Session) -> User | None:
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        return None
    try:
        user_id = parse_session_cookie(cookie)
    except AuthenticationException:
        return None
    return UserRepository(db).get_by_id(user_id)


def require_user_id(request: Request, db: Session) -> int:
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        raise AuthenticationException("Authentication required.")
    user_id = parse_session_cookie(cookie)
    if UserRepository(db).get_by_id(user_id) is None:
        raise AuthenticationException("User not found.")
    return user_id
