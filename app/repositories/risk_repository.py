from datetime import datetime, UTC, timedelta
from typing import Any
from sqlalchemy import func, select, desc, or_
from sqlalchemy.exc import SQLAlchemyError

from app.models.repository import Repository
from app.models.commit import Commit
from app.models.branch import Branch
from app.models.pull_request import PullRequest
from app.models.issue import Issue
from app.models.contributor import Contributor
from app.repositories.base import BaseRepository

def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

class RiskRepository(BaseRepository[Repository]):
    def get_inactive_repositories(self, user_id: int, threshold_days: int = 14) -> list[dict[str, Any]]:
        limit_date = datetime.now(UTC) - timedelta(days=threshold_days)
        try:
            # Subquery to get max committed_at for each repo
            subq = (
                select(Commit.repo_id, func.max(Commit.committed_at).label("last_commit_at"))
                .group_by(Commit.repo_id)
                .subquery()
            )
            
            # Query repositories belonging to user
            stmt = (
                select(Repository, subq.c.last_commit_at)
                .outerjoin(subq, Repository.id == subq.c.repo_id)
                .where(Repository.user_id == user_id)
            )
            
            rows = self.db.execute(stmt).all()
            
            results = []
            for repo, last_commit in rows:
                # If there's a last commit and it's older than threshold, or if there are no commits at all
                if last_commit is None:
                    # No commits ever, let's treat it as inactive if created_at is old
                    repo_created_at = _as_utc(repo.created_at)
                    if repo_created_at < limit_date:
                        results.append({
                            "repo": repo,
                            "last_commit_at": None,
                            "days_inactive": (datetime.now(UTC) - repo_created_at).days
                        })
                elif _as_utc(last_commit) < limit_date:
                    results.append({
                        "repo": repo,
                        "last_commit_at": last_commit,
                        "days_inactive": (datetime.now(UTC) - _as_utc(last_commit)).days
                    })
            return results
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_stale_branches(self, user_id: int, threshold_days: int = 30) -> list[dict[str, Any]]:
        limit_date = datetime.now(UTC) - timedelta(days=threshold_days)
        try:
            # Query all branches in repositories belonging to the user
            stmt = (
                select(Branch, Repository)
                .join(Repository, Branch.repository_id == Repository.id)
                .where(Repository.user_id == user_id)
            )
            rows = self.db.execute(stmt).all()
            
            results = []
            for branch, repo in rows:
                # Find the latest commit on this branch in Commit table
                # We match commits by Commit.repo_id and if Commit.branch_name contains this branch name
                commit_stmt = (
                    select(func.max(Commit.committed_at))
                    .where(
                        Commit.repo_id == branch.repository_id,
                        Commit.branch_name.like(f"%{branch.github_branch_name}%")
                    )
                )
                last_commit = self.db.scalar(commit_stmt)
                
                # Check if branch has commits and the latest is older than threshold
                if last_commit is None:
                    # No commits found in DB. Check synced_at or created_at
                    ref_date = branch.synced_at or branch.created_at
                    if ref_date and _as_utc(ref_date) < limit_date:
                        results.append({
                            "branch": branch,
                            "repo": repo,
                            "last_commit_at": None,
                            "days_inactive": (datetime.now(UTC) - _as_utc(ref_date)).days
                        })
                elif _as_utc(last_commit) < limit_date:
                    results.append({
                        "branch": branch,
                        "repo": repo,
                        "last_commit_at": last_commit,
                        "days_inactive": (datetime.now(UTC) - _as_utc(last_commit)).days
                    })
            return results
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_old_open_prs(self, user_id: int, threshold_days: int = 7) -> list[dict[str, Any]]:
        limit_date = datetime.now(UTC) - timedelta(days=threshold_days)
        try:
            stmt = (
                select(PullRequest, Repository)
                .join(Repository, PullRequest.repo_id == Repository.id)
                .where(
                    Repository.user_id == user_id,
                    PullRequest.state == "open",
                    PullRequest.created_at <= limit_date
                )
                .order_by(desc(PullRequest.created_at))
            )
            rows = self.db.execute(stmt).all()
            return [{"pr": pr, "repo": repo, "days_open": (datetime.now(UTC) - _as_utc(pr.created_at)).days} for pr, repo in rows]
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_old_open_issues(self, user_id: int, threshold_days: int = 30) -> list[dict[str, Any]]:
        limit_date = datetime.now(UTC) - timedelta(days=threshold_days)
        try:
            stmt = (
                select(Issue, Repository)
                .join(Repository, Issue.repo_id == Repository.id)
                .where(
                    Repository.user_id == user_id,
                    Issue.state == "open",
                    Issue.created_at <= limit_date
                )
                .order_by(desc(Issue.created_at))
            )
            rows = self.db.execute(stmt).all()
            return [{"issue": issue, "repo": repo, "days_open": (datetime.now(UTC) - _as_utc(issue.created_at)).days} for issue, repo in rows]
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_inactive_contributors(self, user_id: int, threshold_days: int = 14) -> list[dict[str, Any]]:
        limit_date = datetime.now(UTC) - timedelta(days=threshold_days)
        try:
            # Query all contributors in repositories belonging to the user
            stmt = (
                select(Contributor, Repository)
                .join(Repository, Contributor.repo_id == Repository.id)
                .where(Repository.user_id == user_id)
            )
            rows = self.db.execute(stmt).all()
            
            results = []
            for contributor, repo in rows:
                # Find latest commit for this contributor in the repo
                commit_stmt = (
                    select(func.max(Commit.committed_at))
                    .where(
                        Commit.repo_id == contributor.repo_id,
                        Commit.contributor_id == contributor.id
                    )
                )
                last_commit = self.db.scalar(commit_stmt)
                
                if last_commit is None:
                    # Let's fallback to author_login or email matches
                    fallback_pred = []
                    if contributor.github_login:
                        fallback_pred.append(Commit.author_login == contributor.github_login)
                    if contributor.email:
                        fallback_pred.append(Commit.author_email == contributor.email)
                    
                    if fallback_pred:
                        commit_stmt = (
                            select(func.max(Commit.committed_at))
                            .where(
                                Commit.repo_id == contributor.repo_id,
                                or_(*fallback_pred)
                            )
                        )
                        last_commit = self.db.scalar(commit_stmt)
                
                if last_commit is None:
                    # No commits found, check contributor record created time
                    ref_date = contributor.created_at
                    if ref_date and _as_utc(ref_date) < limit_date:
                        results.append({
                            "contributor": contributor,
                            "repo": repo,
                            "last_commit_at": None,
                            "days_inactive": (datetime.now(UTC) - _as_utc(ref_date)).days
                        })
                elif _as_utc(last_commit) < limit_date:
                    results.append({
                        "contributor": contributor,
                        "repo": repo,
                        "last_commit_at": last_commit,
                        "days_inactive": (datetime.now(UTC) - _as_utc(last_commit)).days
                    })
            return results
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_bus_factor_risks(self, user_id: int, threshold_percentage: float = 0.8) -> list[dict[str, Any]]:
        limit_date = datetime.now(UTC) - timedelta(days=90)
        try:
            # Get repositories of user
            repos = self.db.scalars(select(Repository).where(Repository.user_id == user_id)).all()
            
            results = []
            for repo in repos:
                # Count total commits in last 90 days
                total_commits = self.db.scalar(
                    select(func.count(Commit.id))
                    .where(
                        Commit.repo_id == repo.id,
                        Commit.committed_at >= limit_date
                    )
                )
                
                if not total_commits or total_commits < 5:
                    continue  # Skip repos with low activity to prevent false positives
                
                # Count commits per contributor in last 90 days
                commits_per_author = self.db.execute(
                    select(
                        func.coalesce(Commit.author_login, Commit.author_name).label("author"),
                        func.count(Commit.id).label("count")
                    )
                    .where(
                        Commit.repo_id == repo.id,
                        Commit.committed_at >= limit_date
                    )
                    .group_by(func.coalesce(Commit.author_login, Commit.author_name))
                    .order_by(desc("count"))
                ).all()
                
                if commits_per_author:
                    top_author, top_count = commits_per_author[0]
                    percentage = top_count / total_commits
                    if percentage >= threshold_percentage:
                        results.append({
                            "repo": repo,
                            "top_contributor": top_author,
                            "top_commits": top_count,
                            "total_commits": total_commits,
                            "percentage": percentage
                        })
            return results
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_stale_syncs(self, user_id: int, threshold_hours: int = 24) -> list[dict[str, Any]]:
        limit_date = datetime.now(UTC) - timedelta(hours=threshold_hours)
        try:
            repos = self.db.scalars(
                select(Repository).where(Repository.user_id == user_id)
            ).all()
            
            results = []
            for repo in repos:
                if repo.last_sync_status == "failed":
                    results.append({
                        "repo": repo,
                        "type": "failed",
                        "detail": f"Đồng bộ gần nhất thất bại: {repo.last_sync_error or 'Không có thông tin lỗi'}"
                    })
                elif not repo.last_synced_at:
                    results.append({
                        "repo": repo,
                        "type": "never_synced",
                        "detail": "Chưa từng đồng bộ thành công"
                    })
                elif _as_utc(repo.last_synced_at) < limit_date:
                    hours_ago = int((datetime.now(UTC) - _as_utc(repo.last_synced_at)).total_seconds() / 3600)
                    results.append({
                        "repo": repo,
                        "type": "stale",
                        "detail": f"Đồng bộ gần nhất cách đây {hours_ago} giờ (ngưỡng: {threshold_hours} giờ)"
                    })
            return results
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)
