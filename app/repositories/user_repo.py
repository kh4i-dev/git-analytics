from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def get_by_id(self, user_id: int) -> User | None:
        try:
            return self.db.get(User, user_id)
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_by_github_id(self, github_id: int) -> User | None:
        try:
            return self.db.scalar(select(User).where(User.github_id == github_id))
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def create(self, data: Mapping[str, Any]) -> User:
        user = User(**data)
        self.db.add(user)
        self._flush()
        return user

    def update(self, user: User, data: Mapping[str, Any]) -> User:
        return self._apply_updates(user, data)

    def upsert_by_github_id(self, data: Mapping[str, Any]) -> User:
        github_id = int(data["github_id"])
        user = self.get_by_github_id(github_id)
        if user is None:
            return self.create(data)
        return self.update(user, data)

    def delete(self, user: User) -> None:
        try:
            self.db.delete(user)
            self._flush()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)
