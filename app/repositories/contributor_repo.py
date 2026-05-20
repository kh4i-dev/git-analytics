from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.contributor import Contributor
from app.repositories.base import BaseRepository


class ContributorRepository(BaseRepository[Contributor]):
    def get_by_id(self, contributor_id: int) -> Contributor | None:
        try:
            return self.db.get(Contributor, contributor_id)
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def list_by_repo(
        self,
        repo_id: int,
        *,
        page: int = 1,
        per_page: int = 100,
    ) -> Sequence[Contributor]:
        offset, limit = self._pagination(page, per_page)
        try:
            return self.db.scalars(
                select(Contributor)
                .where(Contributor.repo_id == repo_id)
                .order_by(Contributor.display_name.asc(), Contributor.id.asc())
                .offset(offset)
                .limit(limit)
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_by_identity(
        self,
        repo_id: int,
        *,
        github_login: str | None = None,
        email: str | None = None,
    ) -> Contributor | None:
        try:
            if github_login:
                return self.db.scalar(
                    select(Contributor).where(
                        Contributor.repo_id == repo_id,
                        Contributor.github_login == github_login,
                    )
                )
            if email:
                return self.db.scalar(
                    select(Contributor).where(
                        Contributor.repo_id == repo_id,
                        Contributor.github_login.is_(None),
                        Contributor.email == email,
                    )
                )
            return None
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def create(self, data: Mapping[str, Any]) -> Contributor:
        contributor = Contributor(**data)
        self.db.add(contributor)
        self._flush()
        return contributor

    def update(self, contributor: Contributor, data: Mapping[str, Any]) -> Contributor:
        return self._apply_updates(contributor, data)

    def upsert_by_identity(self, data: Mapping[str, Any]) -> Contributor:
        contributor = self.get_by_identity(
            int(data["repo_id"]),
            github_login=data.get("github_login"),
            email=data.get("email"),
        )
        if contributor is None:
            return self.create(data)
        return self.update(contributor, data)
