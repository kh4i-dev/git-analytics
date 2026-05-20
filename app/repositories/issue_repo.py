from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import func, select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from app.models.issue import Issue
from app.repositories.base import BaseRepository


class IssueRepository(BaseRepository[Issue]):
    def get_by_id(self, issue_id: int) -> Issue | None:
        try:
            return self.db.get(Issue, issue_id)
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_by_repo_number(self, repo_id: int, number: int) -> Issue | None:
        try:
            return self.db.scalar(
                select(Issue).where(
                    Issue.repo_id == repo_id,
                    Issue.number == number,
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
    ) -> Sequence[Issue]:
        offset, limit = self._pagination(page, per_page)
        try:
            return self.db.scalars(
                select(Issue)
                .where(Issue.repo_id == repo_id)
                .order_by(Issue.created_at.desc(), Issue.id.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def create(self, data: Mapping[str, Any]) -> Issue:
        issue = Issue(**data)
        self.db.add(issue)
        self._flush()
        return issue

    def update(self, issue: Issue, data: Mapping[str, Any]) -> Issue:
        return self._apply_updates(issue, data)

    def upsert_many(self, rows: Sequence[Mapping[str, Any]]) -> int:
        if not rows:
            return 0

        keys = {(int(row["repo_id"]), int(row["number"])) for row in rows}
        try:
            existing_issues = self.db.scalars(
                select(Issue).where(tuple_(Issue.repo_id, Issue.number).in_(keys))
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

        existing_by_key = {(issue.repo_id, issue.number): issue for issue in existing_issues}
        count = 0
        for row in rows:
            key = (int(row["repo_id"]), int(row["number"]))
            issue = existing_by_key.get(key)
            if issue is None:
                self.db.add(Issue(**row))
            else:
                self._apply_without_flush(issue, row)
            count += 1
        self._flush()
        return count

    def issues_by_state(self, repo_id: int) -> dict[str, int]:
        try:
            rows = self.db.execute(
                select(Issue.state.label("state"), func.count(Issue.id).label("count"))
                .where(Issue.repo_id == repo_id)
                .group_by(Issue.state)
            ).all()
            return {row.state: row.count for row in rows}
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def _apply_without_flush(self, issue: Issue, data: Mapping[str, Any]) -> None:
        for field, value in data.items():
            setattr(issue, field, value)
