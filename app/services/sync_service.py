import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
from typing import Any, Protocol

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.clients.github_client import GitHubClient
from app.core.exceptions import (
    AppException,
    AuthenticationException,
    ConflictException,
    GitHubRateLimitExceeded,
    RepositoryNotFoundException,
    SyncFailedException,
)
from app.core.security import decrypt_token
from app.models.contributor import Contributor
from app.models.repository import Repository
from app.repositories import (
    BranchRepository,
    CommitRepository,
    ContributorRepository,
    IssueRepository,
    PullRequestRepository,
    RepositoryRepository,
    UserRepository,
)


class GitHubClientProtocol(Protocol):
    async def get_rate_limit(self) -> dict[str, Any]: ...

    async def list_contributors(self, owner: str, repo: str) -> list[dict[str, Any]]: ...

    async def list_commits(
        self,
        owner: str,
        repo: str,
        since: datetime | str | None = None,
        sha: str | None = None,
    ) -> list[dict[str, Any]]: ...

    async def list_branches(self, owner: str, repo: str) -> list[dict[str, Any]]: ...

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "all",
        since: datetime | str | None = None,
    ) -> list[dict[str, Any]]: ...

    async def list_issues(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "all",
        since: datetime | str | None = None,
    ) -> list[dict[str, Any]]: ...

    async def aclose(self) -> None: ...


GitHubClientFactory = Callable[[str], GitHubClientProtocol]
TokenDecrypter = Callable[[str], str]


@dataclass(frozen=True)
class SyncResult:
    repository_id: int
    mode: str
    status: str
    synced: dict[str, int]
    started_at: datetime
    completed_at: datetime


class SyncService:
    def __init__(
        self,
        db: Session,
        *,
        github_client_factory: GitHubClientFactory | None = None,
        token_decrypter: TokenDecrypter = decrypt_token,
        min_rate_limit_remaining: int = 50,
    ) -> None:
        self.db = db
        self.github_client_factory = github_client_factory or (
            lambda token: GitHubClient(token)
        )
        self.token_decrypter = token_decrypter
        self.min_rate_limit_remaining = min_rate_limit_remaining

        self.user_repo = UserRepository(db)
        self.repository_repo = RepositoryRepository(db)
        self.contributor_repo = ContributorRepository(db)
        self.branch_repo = BranchRepository(db)
        self.commit_repo = CommitRepository(db)
        self.pull_request_repo = PullRequestRepository(db)
        self.issue_repo = IssueRepository(db)

    async def sync_repository(self, *, user_id: int, repo_id: int) -> SyncResult:
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise AuthenticationException("User not found.")

        repository = self.repository_repo.get_by_user_and_id(user_id, repo_id)
        if repository is None:
            raise RepositoryNotFoundException("Repository not found.")

        if repository.last_sync_status == "syncing":
            raise ConflictException("Repository sync is already in progress.")

        sync_since = self._ensure_utc(repository.last_synced_at)
        sync_mode = "full" if sync_since is None else "incremental"
        started_at = self._utc_now()

        try:
            access_token = self.token_decrypter(user.encrypted_github_token)
        except Exception as exc:
            self.db.rollback()
            self._mark_failed(repo_id, exc)
            if isinstance(exc, AppException):
                raise
            raise SyncFailedException(self._short_error(exc)) from exc

        client = self.github_client_factory(access_token)
        if hasattr(client, "repo_id"):
            client.repo_id = repository.id

        try:
            await self._check_rate_limit(client)
            self.repository_repo.update_sync_status(
                repository,
                status="syncing",
                last_sync_error=None,
                sync_started_at=started_at,
            )
            self.db.commit()

            synced = await self._sync_data(repository, client, sync_since)
            completed_at = self._utc_now()
            self.repository_repo.update_sync_status(
                repository,
                status="success",
                last_synced_at=completed_at,
                last_sync_error=None,
                sync_started_at=None,
            )
            self.db.commit()

            return SyncResult(
                repository_id=repository.id,
                mode=sync_mode,
                status="success",
                synced=synced,
                started_at=started_at,
                completed_at=completed_at,
            )
        except BaseException as exc:
            self.db.rollback()
            self._mark_failed(repo_id, exc)
            if isinstance(exc, asyncio.CancelledError):
                logger.warning("Repo %s: Sync task was cancelled", repo_id)
                raise
            if isinstance(exc, AppException):
                raise
            raise SyncFailedException(self._short_error(exc)) from exc
        finally:
            await client.aclose()

    async def _check_rate_limit(self, client: GitHubClientProtocol) -> None:
        rate_limit = await client.get_rate_limit()
        remaining = rate_limit.get("remaining")
        if isinstance(remaining, int) and remaining < self.min_rate_limit_remaining:
            raise GitHubRateLimitExceeded(
                "GitHub API rate limit is too low to start sync.",
                details={
                    "remaining": remaining,
                    "required": self.min_rate_limit_remaining,
                    "reset_at": rate_limit.get("reset_at"),
                },
            )

    async def _sync_data(
        self,
        repository: Repository,
        client: GitHubClientProtocol,
        since: datetime | None,
    ) -> dict[str, int]:
        owner = repository.owner
        repo = repository.name
        repo_id = repository.id

        import time

        async def run_step(step_name: str, coro):
            t0 = time.perf_counter()
            logger.info("Repo %s: Starting step '%s'", repo_id, step_name)
            res = await coro
            duration = time.perf_counter() - t0
            logger.info("Repo %s: Completed step '%s' in %.2fs", repo_id, step_name, duration)
            return res

        raw_contributors = await run_step("contributors", client.list_contributors(owner, repo))
        raw_branches = await run_step("branches", self._list_branches(client, repository))
        branches_to_sync = self._branches_to_sync(repository, raw_branches)
        branch_rows = [
            {
                "repository_id": repository.id,
                "github_branch_name": branch["name"],
                "is_default": branch["name"] == repository.default_branch,
                "last_commit_sha": (branch.get("commit") or {}).get("sha"),
            }
            for branch in raw_branches
            if isinstance(branch.get("name"), str)
        ]
        branches_count = self.branch_repo.upsert_many(branch_rows)

        raw_commits: list[dict[str, Any]] = []
        branch_last_sha: dict[str, str | None] = {}
        existing_branches = {
            branch.github_branch_name: branch
            for branch in self.branch_repo.list_by_repo(repository.id)
        }
        for branch_name in branches_to_sync:
            branch = existing_branches.get(branch_name)
            branch_since = self._ensure_utc(branch.synced_at) if branch else None
            if branch_since is None:
                branch_since = since
            
            logger.info("Repo %s: Syncing branch '%s'", repo_id, branch_name)
            branch_commits = await run_step(
                f"commits-branch-{branch_name}",
                self._list_commits_for_branch(
                    client,
                    owner,
                    repo,
                    since=branch_since,
                    branch_name=branch_name,
                )
            )
            if branch_commits:
                branch_last_sha[branch_name] = branch_commits[0].get("sha")
            else:
                branch_last_sha[branch_name] = (
                    branch.last_commit_sha if branch else None
                )
            for raw_commit in branch_commits:
                raw_commit["_branch_name"] = branch_name
                raw_commits.append(raw_commit)

        raw_pull_requests = await run_step(
            "pull_requests",
            client.list_pull_requests(
                owner,
                repo,
                state="all",
                since=since,
            )
        )
        raw_issues = await run_step(
            "issues",
            client.list_issues(owner, repo, state="all", since=since)
        )

        contributors_by_key: dict[tuple[str, str], Contributor] = {}
        for raw_contributor in raw_contributors:
            contributor = self._upsert_contributor(
                repository.id,
                github_login=raw_contributor.get("login"),
                email=None,
                display_name=raw_contributor.get("login") or "Unknown",
                avatar_url=raw_contributor.get("avatar_url"),
            )
            if contributor.github_login:
                contributors_by_key[("login", contributor.github_login)] = contributor

        commit_rows = [
            self._map_commit(repository.id, raw_commit, contributors_by_key)
            for raw_commit in raw_commits
        ]
        pull_request_rows = [
            self._map_pull_request(repository.id, raw_pull_request, contributors_by_key)
            for raw_pull_request in raw_pull_requests
        ]
        issue_rows = [
            self._map_issue(repository.id, raw_issue, contributors_by_key)
            for raw_issue in raw_issues
            if "pull_request" not in raw_issue
        ]

        contributors_count = len(contributors_by_key)
        commits_count = self.commit_repo.upsert_many(commit_rows)
        pull_requests_count = self.pull_request_repo.upsert_many(pull_request_rows)
        issues_count = self.issue_repo.upsert_many(issue_rows)
        synced_at = self._utc_now()
        for branch_name, last_sha in branch_last_sha.items():
            self.branch_repo.mark_synced(
                repository.id,
                branch_name,
                last_commit_sha=last_sha,
                synced_at=synced_at,
            )

        return {
            "branches": branches_count,
            "contributors": contributors_count,
            "commits": commits_count,
            "pull_requests": pull_requests_count,
            "issues": issues_count,
        }

    def _map_commit(
        self,
        repo_id: int,
        raw: dict[str, Any],
        contributors_by_key: dict[tuple[str, str], Contributor],
    ) -> dict[str, Any]:
        commit = raw.get("commit") or {}
        author = commit.get("author") or {}
        committer = commit.get("committer") or {}
        github_author = raw.get("author") or {}
        github_committer = raw.get("committer") or {}
        author_login = github_author.get("login")
        author_email = author.get("email") or ""
        contributor = self._resolve_contributor(
            repo_id,
            contributors_by_key,
            github_login=author_login,
            email=author_email or None,
            display_name=author.get("name") or author_login or author_email or "Unknown",
            avatar_url=github_author.get("avatar_url"),
        )

        return {
            "repo_id": repo_id,
            "contributor_id": contributor.id if contributor else None,
            "sha": raw["sha"],
            "branch_name": raw.get("_branch_name"),
            "message": commit.get("message"),
            "author_name": author.get("name") or author_login or "Unknown",
            "author_email": author_email,
            "author_login": author_login,
            "author_avatar_url": github_author.get("avatar_url"),
            "committer_name": committer.get("name"),
            "committer_email": committer.get("email"),
            "committer_login": github_committer.get("login"),
            "committed_at": self._parse_datetime(author["date"]),
            "html_url": raw["html_url"],
        }

    def _map_pull_request(
        self,
        repo_id: int,
        raw: dict[str, Any],
        contributors_by_key: dict[tuple[str, str], Contributor],
    ) -> dict[str, Any]:
        author = raw.get("user") or {}
        author_login = author.get("login") or "unknown"
        contributor = self._resolve_contributor(
            repo_id,
            contributors_by_key,
            github_login=author_login,
            email=None,
            display_name=author_login,
            avatar_url=author.get("avatar_url"),
        )

        return {
            "repo_id": repo_id,
            "contributor_id": contributor.id if contributor else None,
            "number": raw["number"],
            "title": raw.get("title") or "",
            "base_branch": (raw.get("base") or {}).get("ref"),
            "head_branch": (raw.get("head") or {}).get("ref"),
            "state": raw.get("state") or "closed",
            "is_merged": raw.get("merged_at") is not None,
            "author_login": author_login,
            "author_avatar_url": author.get("avatar_url"),
            "draft": bool(raw.get("draft", False)),
            "created_at": self._parse_datetime(raw["created_at"]),
            "updated_at": self._parse_datetime(raw["updated_at"]),
            "closed_at": self._parse_optional_datetime(raw.get("closed_at")),
            "merged_at": self._parse_optional_datetime(raw.get("merged_at")),
            "html_url": raw["html_url"],
        }

    def _map_issue(
        self,
        repo_id: int,
        raw: dict[str, Any],
        contributors_by_key: dict[tuple[str, str], Contributor],
    ) -> dict[str, Any]:
        author = raw.get("user") or {}
        author_login = author.get("login") or "unknown"
        contributor = self._resolve_contributor(
            repo_id,
            contributors_by_key,
            github_login=author_login,
            email=None,
            display_name=author_login,
            avatar_url=author.get("avatar_url"),
        )

        return {
            "repo_id": repo_id,
            "contributor_id": contributor.id if contributor else None,
            "number": raw["number"],
            "title": raw.get("title") or "",
            "state": raw.get("state") or "closed",
            "author_login": author_login,
            "author_avatar_url": author.get("avatar_url"),
            "labels": self._label_names(raw.get("labels") or []),
            "created_at": self._parse_datetime(raw["created_at"]),
            "updated_at": self._parse_datetime(raw["updated_at"]),
            "closed_at": self._parse_optional_datetime(raw.get("closed_at")),
            "html_url": raw["html_url"],
        }

    def _resolve_contributor(
        self,
        repo_id: int,
        contributors_by_key: dict[tuple[str, str], Contributor],
        *,
        github_login: str | None,
        email: str | None,
        display_name: str,
        avatar_url: str | None,
    ) -> Contributor | None:
        if github_login:
            key = ("login", github_login)
        elif email:
            key = ("email", email)
        else:
            return None

        existing = contributors_by_key.get(key)
        if existing is not None:
            return existing

        contributor = self._upsert_contributor(
            repo_id,
            github_login=github_login,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
        )
        contributors_by_key[key] = contributor
        return contributor

    def _upsert_contributor(
        self,
        repo_id: int,
        *,
        github_login: str | None,
        email: str | None,
        display_name: str,
        avatar_url: str | None,
    ) -> Contributor:
        return self.contributor_repo.upsert_by_identity(
            {
                "repo_id": repo_id,
                "github_login": github_login,
                "email": email,
                "display_name": display_name,
                "avatar_url": avatar_url,
                "source_type": "github_user" if github_login else "git_email",
            }
        )

    async def _list_branches(
        self,
        client: GitHubClientProtocol,
        repository: Repository,
    ) -> list[dict[str, Any]]:
        list_branches = getattr(client, "list_branches", None)
        if list_branches is None:
            return self._default_branch_payload(repository)
        
        # Branch sync timeout: e.g. 30 seconds
        try:
            branches = await asyncio.wait_for(
                list_branches(repository.owner, repository.name),
                timeout=30.0
            )
        except asyncio.TimeoutError as exc:
            logger.error("Repo %s: Branch listing timed out", repository.id)
            raise TimeoutError("Branch listing timed out after 30 seconds") from exc

        if branches:
            return branches
        return self._default_branch_payload(repository)

    async def _list_commits_for_branch(
        self,
        client: GitHubClientProtocol,
        owner: str,
        repo: str,
        *,
        since: datetime | None,
        branch_name: str,
    ) -> list[dict[str, Any]]:
        # Commit pagination timeout: e.g. 60 seconds
        try:
            return await asyncio.wait_for(
                self._list_commits_helper(client, owner, repo, since, branch_name),
                timeout=60.0
            )
        except asyncio.TimeoutError as exc:
            logger.error("Repo %s: Commit listing timed out for branch '%s'", getattr(client, "repo_id", None), branch_name)
            raise TimeoutError(f"Commit listing timed out for branch {branch_name} after 60 seconds") from exc

    async def _list_commits_helper(
        self,
        client: GitHubClientProtocol,
        owner: str,
        repo: str,
        since: datetime | None,
        branch_name: str,
    ) -> list[dict[str, Any]]:
        try:
            return await client.list_commits(owner, repo, since=since, sha=branch_name)
        except TypeError:
            return await client.list_commits(owner, repo, since=since)

    def _default_branch_payload(self, repository: Repository) -> list[dict[str, Any]]:
        branch_name = repository.default_branch or "main"
        return [{"name": branch_name, "commit": {"sha": None}}]

    def _branches_to_sync(
        self,
        repository: Repository,
        raw_branches: list[dict[str, Any]],
    ) -> list[str]:
        names = [
            branch["name"]
            for branch in raw_branches
            if isinstance(branch.get("name"), str)
        ]
        if not names:
            return [repository.default_branch or "main"]

        mode = repository.branch_sync_mode or "default_only"
        if mode == "all":
            return names
        if mode == "selected":
            selected = self._selected_branch_patterns(repository.selected_branches)
            matched = [
                name
                for name in names
                if any(self._branch_matches(name, pattern) for pattern in selected)
            ]
            return matched or [repository.default_branch or names[0]]
        default_branch = repository.default_branch or names[0]
        return [default_branch] if default_branch in names else [names[0]]

    def _selected_branch_patterns(self, value: str | None) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        return []

    def _branch_matches(self, name: str, pattern: str) -> bool:
        if pattern == name:
            return True
        if "*" not in pattern:
            return False
        prefix, _, suffix = pattern.partition("*")
        return name.startswith(prefix) and name.endswith(suffix)

    def _mark_failed(self, repo_id: int, exc: BaseException) -> None:
        try:
            repository = self.repository_repo.get_by_id(repo_id)
            if repository is None:
                return
            self.repository_repo.update_sync_status(
                repository,
                status="failed",
                last_sync_error=self._short_error(exc),
                sync_started_at=None,
            )
            self.db.commit()
        except BaseException:
            self.db.rollback()

    def _label_names(self, labels: list[Any]) -> list[str]:
        names: list[str] = []
        for label in labels:
            if isinstance(label, dict) and isinstance(label.get("name"), str):
                names.append(label["name"])
            elif isinstance(label, str):
                names.append(label)
        return names

    def _parse_optional_datetime(self, value: str | None) -> datetime | None:
        if value is None:
            return None
        return self._parse_datetime(value)

    def _parse_datetime(self, value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _utc_now(self) -> datetime:
        return datetime.now(UTC)

    def _ensure_utc(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _short_error(self, exc: Exception) -> str:
        message = getattr(exc, "message", str(exc)) or exc.__class__.__name__
        return message[:500]
