from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from app.models.branch import Branch
from app.repositories.base import BaseRepository


class BranchRepository(BaseRepository[Branch]):
    def get_by_id(self, branch_id: int) -> Branch | None:
        try:
            return self.db.get(Branch, branch_id)
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def list_by_repo(self, repository_id: int) -> Sequence[Branch]:
        try:
            return self.db.scalars(
                select(Branch)
                .where(Branch.repository_id == repository_id)
                .order_by(Branch.is_default.desc(), Branch.github_branch_name.asc())
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def create(self, data: Mapping[str, Any]) -> Branch:
        branch = Branch(**data)
        self.db.add(branch)
        self._flush()
        return branch

    def update(self, branch: Branch, data: Mapping[str, Any]) -> Branch:
        return self._apply_updates(branch, data)

    def upsert_many(self, rows: Sequence[Mapping[str, Any]]) -> int:
        if not rows:
            return 0

        keys = {
            (int(row["repository_id"]), str(row["github_branch_name"]))
            for row in rows
        }
        try:
            existing = self.db.scalars(
                select(Branch).where(
                    tuple_(Branch.repository_id, Branch.github_branch_name).in_(keys)
                )
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

        existing_by_key = {
            (branch.repository_id, branch.github_branch_name): branch
            for branch in existing
        }
        count = 0
        for row in rows:
            key = (int(row["repository_id"]), str(row["github_branch_name"]))
            branch = existing_by_key.get(key)
            if branch is None:
                self.db.add(Branch(**row))
            else:
                for field, value in row.items():
                    setattr(branch, field, value)
            count += 1
        self._flush()
        return count

    def mark_synced(
        self,
        repository_id: int,
        branch_name: str,
        *,
        last_commit_sha: str | None,
        synced_at: datetime,
    ) -> Branch | None:
        try:
            branch = self.db.scalar(
                select(Branch).where(
                    Branch.repository_id == repository_id,
                    Branch.github_branch_name == branch_name,
                )
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

        if branch is None:
            return None
        branch.last_commit_sha = last_commit_sha
        branch.synced_at = synced_at
        self._flush()
        return branch
