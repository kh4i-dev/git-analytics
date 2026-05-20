from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import case, func, select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from app.models.pull_request import PullRequest
from app.repositories.base import BaseRepository


class PullRequestRepository(BaseRepository[PullRequest]):
    def get_by_id(self, pull_request_id: int) -> PullRequest | None:
        try:
            return self.db.get(PullRequest, pull_request_id)
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_by_repo_number(self, repo_id: int, number: int) -> PullRequest | None:
        try:
            return self.db.scalar(
                select(PullRequest).where(
                    PullRequest.repo_id == repo_id,
                    PullRequest.number == number,
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
    ) -> Sequence[PullRequest]:
        offset, limit = self._pagination(page, per_page)
        try:
            return self.db.scalars(
                select(PullRequest)
                .where(PullRequest.repo_id == repo_id)
                .order_by(PullRequest.created_at.desc(), PullRequest.id.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def create(self, data: Mapping[str, Any]) -> PullRequest:
        pull_request = PullRequest(**data)
        self.db.add(pull_request)
        self._flush()
        return pull_request

    def update(
        self,
        pull_request: PullRequest,
        data: Mapping[str, Any],
    ) -> PullRequest:
        return self._apply_updates(pull_request, data)

    def upsert_many(self, rows: Sequence[Mapping[str, Any]]) -> int:
        if not rows:
            return 0

        keys = {(int(row["repo_id"]), int(row["number"])) for row in rows}
        try:
            existing_pull_requests = self.db.scalars(
                select(PullRequest).where(
                    tuple_(PullRequest.repo_id, PullRequest.number).in_(keys)
                )
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

        existing_by_key = {
            (pull_request.repo_id, pull_request.number): pull_request
            for pull_request in existing_pull_requests
        }
        count = 0
        for row in rows:
            key = (int(row["repo_id"]), int(row["number"]))
            pull_request = existing_by_key.get(key)
            if pull_request is None:
                self.db.add(PullRequest(**row))
            else:
                self._apply_without_flush(pull_request, row)
            count += 1
        self._flush()
        return count

    def pr_status_summary(self, repo_id: int) -> dict[str, int]:
        try:
            rows = self.db.execute(
                select(
                    PullRequest.state.label("state"),
                    PullRequest.is_merged.label("is_merged"),
                    func.count(PullRequest.id).label("count"),
                )
                .where(PullRequest.repo_id == repo_id)
                .group_by(PullRequest.state, PullRequest.is_merged)
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

        summary = {"open": 0, "closed": 0, "merged": 0}
        for row in rows:
            if row.is_merged:
                summary["merged"] += row.count
            elif row.state == "open":
                summary["open"] += row.count
            else:
                summary["closed"] += row.count
        return summary

    def merged_count(self, repo_id: int) -> int:
        try:
            return self.db.scalar(
                select(
                    func.coalesce(
                        func.sum(case((PullRequest.is_merged.is_(True), 1), else_=0)),
                        0,
                    )
                ).where(PullRequest.repo_id == repo_id)
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def _apply_without_flush(
        self,
        pull_request: PullRequest,
        data: Mapping[str, Any],
    ) -> None:
        for field, value in data.items():
            setattr(pull_request, field, value)
