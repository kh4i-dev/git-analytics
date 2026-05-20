from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.repository import Repository
from app.repositories.base import BaseRepository


class RepositoryRepository(BaseRepository[Repository]):
    def get_by_id(self, repository_id: int) -> Repository | None:
        try:
            return self.db.get(Repository, repository_id)
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_by_user_and_id(self, user_id: int, repository_id: int) -> Repository | None:
        try:
            return self.db.scalar(
                select(Repository).where(
                    Repository.user_id == user_id,
                    Repository.id == repository_id,
                )
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_by_user_github_repo_id(
        self,
        user_id: int,
        github_repo_id: int,
    ) -> Repository | None:
        try:
            return self.db.scalar(
                select(Repository).where(
                    Repository.user_id == user_id,
                    Repository.github_repo_id == github_repo_id,
                )
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def list_by_user(
        self,
        user_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> Sequence[Repository]:
        offset, limit = self._pagination(page, per_page)
        try:
            return self.db.scalars(
                select(Repository)
                .where(Repository.user_id == user_id)
                .order_by(Repository.created_at.desc(), Repository.id.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def create(self, data: Mapping[str, Any]) -> Repository:
        repository = Repository(**data)
        self.db.add(repository)
        self._flush()
        return repository

    def update(self, repository: Repository, data: Mapping[str, Any]) -> Repository:
        return self._apply_updates(repository, data)

    def upsert_by_user_github_repo_id(
        self,
        user_id: int,
        github_repo_id: int,
        data: Mapping[str, Any],
    ) -> Repository:
        existing = self.get_by_user_github_repo_id(user_id, github_repo_id)
        if existing is None:
            return self.create({"user_id": user_id, "github_repo_id": github_repo_id, **data})
        return self.update(existing, data)

    def update_sync_status(
        self,
        repository: Repository,
        *,
        status: str,
        last_synced_at: datetime | None = None,
        last_sync_error: str | None = None,
        sync_started_at: datetime | None = None,
    ) -> Repository:
        repository.last_sync_status = status
        repository.last_sync_error = last_sync_error
        repository.sync_started_at = sync_started_at
        if last_synced_at is not None:
            repository.last_synced_at = last_synced_at
        self._flush()
        return repository

    def delete(self, repository: Repository) -> None:
        try:
            self.db.delete(repository)
            self._flush()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)
