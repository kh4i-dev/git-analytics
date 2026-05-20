from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import func, select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from app.models.commit import Commit
from app.models.contributor import Contributor
from app.repositories.base import BaseRepository


class CommitRepository(BaseRepository[Commit]):
    def get_by_id(self, commit_id: int) -> Commit | None:
        try:
            return self.db.get(Commit, commit_id)
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_by_repo_sha(self, repo_id: int, sha: str) -> Commit | None:
        try:
            return self.db.scalar(
                select(Commit).where(
                    Commit.repo_id == repo_id,
                    Commit.sha == sha,
                )
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def list_by_repo(
        self,
        repo_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> Sequence[Commit]:
        offset, limit = self._pagination(page, per_page)
        try:
            return self.db.scalars(
                select(Commit)
                .where(Commit.repo_id == repo_id)
                .order_by(Commit.committed_at.desc(), Commit.id.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def create(self, data: Mapping[str, Any]) -> Commit:
        commit = Commit(**data)
        self.db.add(commit)
        self._flush()
        return commit

    def update(self, commit: Commit, data: Mapping[str, Any]) -> Commit:
        return self._apply_updates(commit, data)

    def upsert_many(self, rows: Sequence[Mapping[str, Any]]) -> int:
        if not rows:
            return 0

        keys = {(int(row["repo_id"]), str(row["sha"])) for row in rows}
        try:
            existing_commits = self.db.scalars(
                select(Commit).where(tuple_(Commit.repo_id, Commit.sha).in_(keys))
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

        existing_by_key = {
            (commit.repo_id, commit.sha): commit for commit in existing_commits
        }
        count = 0
        for row in rows:
            key = (int(row["repo_id"]), str(row["sha"]))
            commit = existing_by_key.get(key)
            if commit is None:
                self.db.add(Commit(**row))
            else:
                self._apply_without_flush(commit, row)
            count += 1
        self._flush()
        return count

    def commits_per_day(self, repo_id: int) -> list[dict[str, Any]]:
        try:
            rows = self.db.execute(
                select(
                    func.date(Commit.committed_at).label("date"),
                    func.count(Commit.id).label("count"),
                )
                .where(Commit.repo_id == repo_id)
                .group_by(func.date(Commit.committed_at))
                .order_by(func.date(Commit.committed_at))
            ).all()
            return [{"date": str(row.date), "count": row.count} for row in rows]
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def commits_by_contributor(self, repo_id: int) -> list[dict[str, Any]]:
        try:
            rows = self.db.execute(
                select(
                    func.coalesce(
                        Contributor.display_name,
                        Commit.author_login,
                        Commit.author_name,
                    ).label("contributor"),
                    Commit.author_login.label("github_login"),
                    Commit.author_avatar_url.label("avatar_url"),
                    func.count(Commit.id).label("count"),
                )
                .select_from(Commit)
                .join(Contributor, Commit.contributor_id == Contributor.id, isouter=True)
                .where(Commit.repo_id == repo_id)
                .group_by(
                    Contributor.display_name,
                    Commit.author_login,
                    Commit.author_name,
                    Commit.author_avatar_url,
                )
                .order_by(func.count(Commit.id).desc())
            ).all()
            return [
                {
                    "contributor": row.contributor,
                    "github_login": row.github_login,
                    "avatar_url": row.avatar_url,
                    "count": row.count,
                }
                for row in rows
            ]
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def _apply_without_flush(self, commit: Commit, data: Mapping[str, Any]) -> None:
        for field, value in data.items():
            setattr(commit, field, value)
