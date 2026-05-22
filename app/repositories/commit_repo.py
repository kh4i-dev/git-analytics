from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from app.models.commit import Commit
from app.models.contributor import Contributor
from app.repositories.base import BaseRepository


def _branch_predicate(branch_filter: str | None):
    if not branch_filter or branch_filter == "all":
        return None
    if "*" in branch_filter:
        return Commit.branch_name.like(branch_filter.replace("*", "%"))
    return or_(
        Commit.branch_name == branch_filter,
        Commit.branch_name.like(f"{branch_filter},%"),
        Commit.branch_name.like(f"%,{branch_filter}"),
        Commit.branch_name.like(f"%,{branch_filter},%"),
    )


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
        branch_filter: str | None = None,
    ) -> Sequence[Commit]:
        offset, limit = self._pagination(page, per_page)
        predicates = [Commit.repo_id == repo_id]
        branch_predicate = _branch_predicate(branch_filter)
        if branch_predicate is not None:
            predicates.append(branch_predicate)
        try:
            return self.db.scalars(
                select(Commit)
                .where(*predicates)
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

        merged_rows = self._merge_rows_by_sha(rows)
        keys = {(int(row["repo_id"]), str(row["sha"])) for row in merged_rows}
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
        for row in merged_rows:
            key = (int(row["repo_id"]), str(row["sha"]))
            commit = existing_by_key.get(key)
            if commit is None:
                self.db.add(Commit(**row))
            else:
                self._apply_without_flush(commit, row)
            count += 1
        self._flush()
        return count

    def commits_per_day(
        self,
        repo_id: int,
        branch_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        predicates = [Commit.repo_id == repo_id]
        branch_predicate = _branch_predicate(branch_filter)
        if branch_predicate is not None:
            predicates.append(branch_predicate)
        try:
            rows = self.db.execute(
                select(
                    func.date(Commit.committed_at).label("date"),
                    func.count(Commit.id).label("count"),
                )
                .where(*predicates)
                .group_by(func.date(Commit.committed_at))
                .order_by(func.date(Commit.committed_at))
            ).all()
            return [{"date": str(row.date), "count": row.count} for row in rows]
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def commits_by_contributor(
        self,
        repo_id: int,
        branch_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        predicates = [Commit.repo_id == repo_id]
        branch_predicate = _branch_predicate(branch_filter)
        if branch_predicate is not None:
            predicates.append(branch_predicate)
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
                .where(*predicates)
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

    def commits_by_weekday(
        self,
        repo_id: int,
        branch_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Returns commit counts grouped by day-of-week (0=Sun … 6=Sat)."""
        day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        predicates = [Commit.repo_id == repo_id]
        branch_predicate = _branch_predicate(branch_filter)
        if branch_predicate is not None:
            predicates.append(branch_predicate)
        try:
            rows = self.db.execute(
                select(
                    func.strftime("%w", Commit.committed_at).label("weekday"),
                    func.count(Commit.id).label("count"),
                )
                .where(*predicates)
                .group_by(func.strftime("%w", Commit.committed_at))
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

        counts = {i: 0 for i in range(7)}
        for row in rows:
            if row.weekday is not None:
                counts[int(row.weekday)] = row.count
        return [
            {"day": day_names[i], "day_index": i, "count": counts[i]}
            for i in range(7)
        ]

    def commits_by_hour(
        self,
        repo_id: int,
        branch_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Returns commit counts grouped by hour-of-day (0-23, UTC)."""
        predicates = [Commit.repo_id == repo_id]
        branch_predicate = _branch_predicate(branch_filter)
        if branch_predicate is not None:
            predicates.append(branch_predicate)
        try:
            rows = self.db.execute(
                select(
                    func.strftime("%H", Commit.committed_at).label("hour"),
                    func.count(Commit.id).label("count"),
                )
                .where(*predicates)
                .group_by(func.strftime("%H", Commit.committed_at))
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

        counts = {i: 0 for i in range(24)}
        for row in rows:
            if row.hour is not None:
                counts[int(row.hour)] = row.count
        return [{"hour": i, "count": counts[i]} for i in range(24)]

    def get_recent_messages(
        self,
        repo_id: int,
        limit: int = 500,
        branch_filter: str | None = None,
    ) -> list[str]:
        """Returns recent commit messages for keyword analysis."""
        predicates = [Commit.repo_id == repo_id, Commit.message.is_not(None)]
        branch_predicate = _branch_predicate(branch_filter)
        if branch_predicate is not None:
            predicates.append(branch_predicate)
        try:
            return list(
                self.db.scalars(
                    select(Commit.message)
                    .where(*predicates)
                    .order_by(Commit.committed_at.desc())
                    .limit(limit)
                ).all()
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def _apply_without_flush(self, commit: Commit, data: Mapping[str, Any]) -> None:
        for field, value in data.items():
            if field == "branch_name" and commit.branch_name and value:
                names = {
                    name.strip()
                    for name in commit.branch_name.split(",")
                    if name.strip()
                }
                names.add(str(value))
                value = ",".join(sorted(names))
            setattr(commit, field, value)

    def _merge_rows_by_sha(
        self,
        rows: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        merged: dict[tuple[int, str], dict[str, Any]] = {}
        for row in rows:
            key = (int(row["repo_id"]), str(row["sha"]))
            current = merged.get(key)
            if current is None:
                merged[key] = dict(row)
                continue

            branch_names = {
                name.strip()
                for value in (current.get("branch_name"), row.get("branch_name"))
                if value
                for name in str(value).split(",")
                if name.strip()
            }
            current.update(row)
            current["branch_name"] = ",".join(sorted(branch_names)) or None
        return list(merged.values())
