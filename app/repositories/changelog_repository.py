from collections.abc import Sequence
from datetime import datetime
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.models.commit import Commit
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

class ChangelogRepository(BaseRepository[Commit]):
    def get_commits_for_changelog(
        self,
        repo_id: int,
        branch: str | None = None,
        from_date: datetime | str | None = None,
        to_date: datetime | str | None = None,
    ) -> Sequence[Commit]:
        predicates = [Commit.repo_id == repo_id]
        
        branch_pred = _branch_predicate(branch)
        if branch_pred is not None:
            predicates.append(branch_pred)
            
        if from_date:
            if isinstance(from_date, str):
                from_date_dt = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
            else:
                from_date_dt = from_date
            predicates.append(Commit.committed_at >= from_date_dt)
            
        if to_date:
            if isinstance(to_date, str):
                to_date_dt = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
            else:
                to_date_dt = to_date
            predicates.append(Commit.committed_at <= to_date_dt)
            
        try:
            return self.db.scalars(
                select(Commit)
                .where(*predicates)
                .order_by(Commit.committed_at.desc(), Commit.id.desc())
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)
