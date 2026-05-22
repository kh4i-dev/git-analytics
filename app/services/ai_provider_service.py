from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.exceptions import AIProviderException, AIRateLimitException, ValidationException
from app.repositories.ai_usage_repository import AiUsageRepository
from app.services.ai_settings_service import AiSettingsService


@dataclass(frozen=True)
class AiCompletion:
    text: str
    usage_units: int | None = None


class AiProviderGateway:
    def __init__(
        self,
        *,
        app_settings: Settings = settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = app_settings
        self.http_client = http_client

    async def complete(
        self,
        *,
        mode: str,
        provider: str,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
    ) -> AiCompletion:
        if provider == "openai":
            return await self._complete_openai(
                mode=mode,
                api_key=api_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        if provider == "gemini":
            return await self._complete_gemini(
                api_key=api_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        if provider == "claude":
            return await self._complete_claude(
                api_key=api_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        if provider == "nvidia":
            return await self._complete_nvidia(
                api_key=api_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        raise ValidationException("Invalid AI provider.")

    async def _complete_nvidia(
        self,
        *,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
    ) -> AiCompletion:
        base_url = "https://integrate.api.nvidia.com/v1"
        model = self.settings.nvidia_model
        payload = await self._post_json(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json_body={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            },
        )
        choices = payload.get("choices") or []
        content = ((choices[0] if choices else {}).get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise AIProviderException("AI provider returned no text.")
        usage = payload.get("usage") or {}
        return AiCompletion(text=content.strip(), usage_units=_usage_total(usage))

    async def _complete_openai(
        self,
        *,
        mode: str,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
    ) -> AiCompletion:
        use_compatible_gateway = mode == "cloud" and bool(
            self.settings.openai_compatible_base_url
        )
        base_url = (
            self.settings.openai_compatible_base_url.rstrip("/")
            if use_compatible_gateway and self.settings.openai_compatible_base_url
            else "https://api.openai.com/v1"
        )
        model = (
            self.settings.openai_compatible_model or self.settings.openai_model
            if use_compatible_gateway
            else self.settings.openai_model
        )
        payload = await self._post_json(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json_body={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            },
        )
        choices = payload.get("choices") or []
        content = ((choices[0] if choices else {}).get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise AIProviderException("AI provider returned no text.")
        usage = payload.get("usage") or {}
        return AiCompletion(text=content.strip(), usage_units=_usage_total(usage))

    async def _complete_gemini(
        self,
        *,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
    ) -> AiCompletion:
        payload = await self._post_json(
            (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.settings.gemini_model}:generateContent"
            ),
            headers={"x-goog-api-key": api_key},
            json_body={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {"temperature": 0.2},
            },
        )
        candidates = payload.get("candidates") or []
        parts = ((candidates[0] if candidates else {}).get("content") or {}).get("parts") or []
        text = "\n".join(
            part["text"].strip()
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ).strip()
        if not text:
            raise AIProviderException("AI provider returned no text.")
        metadata = payload.get("usageMetadata") or {}
        return AiCompletion(text=text, usage_units=_usage_total(metadata))

    async def _complete_claude(
        self,
        *,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
    ) -> AiCompletion:
        payload = await self._post_json(
            "https://api.anthropic.com/v1/messages",
            headers={
                "anthropic-version": "2023-06-01",
                "x-api-key": api_key,
            },
            json_body={
                "model": self.settings.claude_model,
                "max_tokens": 1200,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
                "temperature": 0.2,
            },
        )
        content = payload.get("content") or []
        text = "\n".join(
            item["text"].strip()
            for item in content
            if isinstance(item, dict)
            and item.get("type") == "text"
            and isinstance(item.get("text"), str)
        ).strip()
        if not text:
            raise AIProviderException("AI provider returned no text.")
        return AiCompletion(text=text, usage_units=_usage_total(payload.get("usage") or {}))

    async def _post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            if self.http_client is not None:
                response = await self.http_client.post(
                    url,
                    headers=headers,
                    json=json_body,
                )
            else:
                async with httpx.AsyncClient(
                    timeout=self.settings.ai_provider_timeout_seconds,
                ) as client:
                    response = await client.post(url, headers=headers, json=json_body)
        except httpx.HTTPError as exc:
            raise AIProviderException("AI provider request could not be completed.") from exc

        if response.status_code in (401, 403):
            raise ValidationException(
                "Invalid API key configured for the AI provider. Please check your key in Settings."
            )
        if response.status_code == 429:
            raise AIRateLimitException("AI provider rate limit exceeded.")
        if response.status_code >= 400:
            raise AIProviderException("AI provider rejected the request.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise AIProviderException("AI provider returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise AIProviderException("AI provider returned invalid JSON.")
        return payload


# Module-level in-memory cache for assistant context, strictly isolated by repo and branch
# Format: { "repo_assistant:{repo_id}:{branch}": cached_data_dict }
_assistant_cache: dict[str, Any] = {}


class AiToolService:
    def __init__(
        self,
        db: Session,
        *,
        app_settings: Settings = settings,
        gateway: AiProviderGateway | None = None,
    ) -> None:
        self.db = db
        self.settings = app_settings
        self.settings_service = AiSettingsService(db, app_settings=app_settings)
        self.usage_repo = AiUsageRepository(db)
        self.gateway = gateway or AiProviderGateway(app_settings=app_settings)

    def clear_context_cache(self, repo_id: int, branch: str | None = None) -> None:
        active_branch = branch or "main"
        cache_key = f"repo_assistant:{repo_id}:{active_branch}"
        if cache_key in _assistant_cache:
            del _assistant_cache[cache_key]

    async def generate_commit_message(self, *, user_id: int, diff: str) -> dict[str, Any]:
        clean_diff = self._validate_input(diff, "diff")
        self._validate_git_diff(clean_diff)
        completion = await self._complete(
            user_id=user_id,
            operation="commit_message",
            system_prompt=(
                "Generate one concise Conventional Commit message for the provided git diff. "
                "Return only the commit message."
            ),
            user_prompt=clean_diff,
        )
        message = completion.text.splitlines()[0].strip().strip("`")
        metadata = self.settings_service.get_active_provider_metadata(user_id)
        return {
            "message": message[:240],
            "files": _changed_files(clean_diff)[:12],
            "metadata": metadata,
        }

    async def review_diff(self, *, user_id: int, diff: str) -> dict[str, Any]:
        clean_diff = self._validate_input(diff, "diff")
        self._validate_git_diff(clean_diff)
        completion = await self._complete(
            user_id=user_id,
            operation="pr_review",
            system_prompt=(
                "Review the provided pull request diff for correctness, security, "
                "reliability, and missing tests. Return concise plain text."
            ),
            user_prompt=clean_diff,
        )
        metadata = self.settings_service.get_active_provider_metadata(user_id)
        return {
            "findings": [
                {
                    "type": "provider",
                    "title": "Provider review",
                    "detail": completion.text[:5000],
                }
            ],
            "files": _changed_files(clean_diff)[:12],
            "metadata": metadata,
        }

    async def answer_question(
        self,
        *,
        user_id: int,
        question: str,
        repo_id: int | None = None,
        branch: str | None = None,
    ) -> dict[str, Any]:
        clean_question = self._validate_input(question, "question")
        
        # Initialize context containers
        system_context_injection = ""
        context_metadata = {
            "repo_name": None,
            "branch": None,
            "retrieved_files": [],
            "repository_source": None,
            "retrieved_chunk_count": 0
        }
        
        # 1. Load repository context if repo_id is supplied
        if repo_id:
            from app.repositories.repository_repo import RepositoryRepository
            repo = RepositoryRepository(self.db).get_by_user_and_id(user_id, repo_id)
            if repo:
                context_metadata["repo_name"] = repo.full_name
                active_branch = branch or repo.default_branch or "main"
                context_metadata["branch"] = active_branch
                
                # Check for context isolation boundaries: only the local "git-analytics" codebase is indexed.
                is_indexed = (repo.name.lower() == "git-analytics" or "git-analytics" in repo.full_name.lower())
                cache_key = f"repo_assistant:{repo_id}:{active_branch}"
                
                if not is_indexed:
                    # Satisfies safety requirements: empty/non-indexed repos return standard message immediately
                    metadata = self.settings_service.get_active_provider_metadata(user_id)
                    context_metadata["repository_source"] = "Empty/Non-indexed"
                    context_metadata["retrieved_chunk_count"] = 0
                    
                    # Cache this response specifically under repo_assistant:{repo_id}:{branch}
                    _assistant_cache[cache_key] = {
                        "answer": "No indexed source files available for this repository.",
                        "mode": "configured_provider",
                        "metadata": metadata,
                        "context_metadata": context_metadata,
                    }
                    return _assistant_cache[cache_key]
                
                # We are in the indexed repository (git-analytics). Load or search context snippets.
                retrieved_snippets = []
                
                if cache_key in _assistant_cache:
                    cached_data = _assistant_cache[cache_key]
                    retrieved_snippets = cached_data.get("snippets", [])
                    context_metadata["retrieved_files"] = cached_data.get("retrieved_files", [])
                    context_metadata["repository_source"] = cached_data.get("repository_source", "Local Workspace")
                    context_metadata["retrieved_chunk_count"] = len(retrieved_snippets)
                else:
                    # Fetch recent commits, PRs, issues as visual summaries
                    commits_count = len(repo.commits)
                    pr_count = len(repo.pull_requests)
                    issue_count = len(repo.issues)
                    contributors_count = len(repo.contributors)
                    branches_list = [b.github_branch_name for b in repo.branches]
                    
                    recent_commits = "\n".join(
                        f"- {c.sha[:8]} by {c.author_name or 'unknown'}: {c.message.splitlines()[0] if c.message else ''}"
                        for c in repo.commits[:5]
                    )
                    recent_prs = "\n".join(
                        f"- PR #{p.number} [{p.state}]: {p.title}"
                        for p in repo.pull_requests[:5]
                    )
                    recent_issues = "\n".join(
                        f"- Issue #{i.number} [{i.state}]: {i.title}"
                        for i in repo.issues[:5]
                    )
                    
                    # Load baseline Grapuco Architecture summary
                    arch_summary = ""
                    try:
                        import os
                        arch_path = os.path.join("docs", "grapuco-architecture-summary.md")
                        if os.path.exists(arch_path):
                            with open(arch_path, "r", encoding="utf-8") as f:
                                arch_summary = f.read()
                                context_metadata["retrieved_files"].append("docs/grapuco-architecture-summary.md")
                    except Exception:
                        pass
                    
                    # 2. Keyword-driven source snippet retrieval
                    question_lower = clean_question.lower()
                    
                    import os
                    # Map keywords to files we want to fetch context from
                    retrieval_map = {
                        ("sync", "đồng bộ", "pipeline", "queue", "worker"): [
                            "app/services/sync_service.py",
                            "app/routes/api_sync.py",
                            "app/models/sync_job.py"
                        ],
                        ("auth", "đăng nhập", "login", "oauth", "session", "cookie"): [
                            "app/routes/auth.py",
                            "app/services/auth_service.py",
                            "app/core/session.py"
                        ],
                        ("analytics", "thống kê", "biểu đồ", "chart", "metrics"): [
                            "app/services/analytics_service.py",
                            "app/routes/api_analytics.py"
                        ],
                        ("report", "báo cáo", "immutable", "snapshot"): [
                            "app/services/engineering_report_service.py",
                            "app/routes/engineering_reports.py"
                        ],
                        ("model", "database", "db", "bảng", "schema"): [
                            "app/models/repository.py",
                            "app/models/user.py",
                            "app/models/commit.py"
                        ]
                    }
                    
                    files_to_read = []
                    for keywords, paths in retrieval_map.items():
                        if any(kw in question_lower for kw in keywords):
                            files_to_read.extend(paths)
                    
                    # De-duplicate files
                    files_to_read = list(dict.fromkeys(files_to_read))[:2]  # Limit to 2 files to keep token usage sane
                    
                    for file_path in files_to_read:
                        try:
                            if os.path.exists(file_path):
                                with open(file_path, "r", encoding="utf-8") as f:
                                    # Read first 120 lines
                                    lines = f.readlines()
                                    snippet = "".join(lines[:120])
                                    retrieved_snippets.append(
                                        f"=== FILE: {file_path} ===\n{snippet}\n=========================="
                                    )
                                    context_metadata["retrieved_files"].append(file_path)
                        except Exception:
                            pass
                    
                    # Store retrieved snippets and files list in cache
                    _assistant_cache[cache_key] = {
                        "snippets": retrieved_snippets,
                        "retrieved_files": context_metadata["retrieved_files"],
                        "repository_source": "Local Workspace"
                    }
                    context_metadata["repository_source"] = "Local Workspace"
                    context_metadata["retrieved_chunk_count"] = len(retrieved_snippets)
                
                snippets_text = "\n\n".join(retrieved_snippets)
                
                # Fetch fresh metadata for instructions Injection
                commits_count = len(repo.commits)
                pr_count = len(repo.pull_requests)
                issue_count = len(repo.issues)
                contributors_count = len(repo.contributors)
                branches_list = [b.github_branch_name for b in repo.branches]
                
                recent_commits = "\n".join(
                    f"- {c.sha[:8]} by {c.author_name or 'unknown'}: {c.message.splitlines()[0] if c.message else ''}"
                    for c in repo.commits[:5]
                )
                recent_prs = "\n".join(
                    f"- PR #{p.number} [{p.state}]: {p.title}"
                    for p in repo.pull_requests[:5]
                )
                recent_issues = "\n".join(
                    f"- Issue #{i.number} [{i.state}]: {i.title}"
                    for i in repo.issues[:5]
                )
                
                arch_summary = ""
                try:
                    import os
                    arch_path = os.path.join("docs", "grapuco-architecture-summary.md")
                    if os.path.exists(arch_path):
                        with open(arch_path, "r", encoding="utf-8") as f:
                            arch_summary = f.read()
                except Exception:
                    pass

                system_context_injection = f"""
You are a repository-aware engineering copilot. You have full indexed context of the repository, branch, and codebase architecture.

REPOSITORY SCOPE:
- Full Name: {repo.full_name}
- Language: {repo.language or "Unknown"}
- Active Scoped Branch: {active_branch}
- Total Synced Branches: {", ".join(branches_list) if branches_list else "None"}
- Sync Stats: {commits_count} commits, {pr_count} PRs, {issue_count} issues, {contributors_count} contributors.

RECENT ACTIVITY SUMMARY:
Commits:
{recent_commits or "None"}

Pull Requests:
{recent_prs or "None"}

Issues:
{recent_issues or "None"}

GRAPUCO ARCHITECTURE KNOWLEDGE SNAPSHOT:
{arch_summary or "None"}

{f"RELEVANT SOURCE CODE RETRIEVED FROM SCOPED DIRECTORY: {snippets_text}" if snippets_text else ""}

GUIDELINES FOR RESPONDING:
1. Answer questions based specifically on the Grapuco Architecture summary and any retrieved source files provided above.
2. NEVER say "please provide the code files", "I don't have access to the repository", or "I need you to paste the code". You already possess the indexed context! 
3. Use a precise, professional, architecture-aware, and repository-specific engineering style. 
4. Reference exact folders, services, models, and controllers where applicable.
"""

        base_prompt = (
            "You are an expert engineering assistant. Provide helpful, accurate, "
            "and concise answers about software development."
        )
        compiled_system_prompt = base_prompt + "\n" + system_context_injection if system_context_injection else base_prompt
        
        completion = await self._complete(
            user_id=user_id,
            operation="repo_assistant",
            system_prompt=compiled_system_prompt,
            user_prompt=clean_question,
        )
        
        metadata = self.settings_service.get_active_provider_metadata(user_id)
        return {
            "answer": completion.text[:8000],
            "mode": "configured_provider",
            "metadata": metadata,
            "context_metadata": context_metadata,
        }

    async def _complete(
        self,
        *,
        user_id: int,
        operation: str,
        system_prompt: str,
        user_prompt: str,
    ) -> AiCompletion:
        current = self.settings_service.get_settings(user_id)
        mode = current["mode"]
        provider, api_key = self.settings_service.get_execution_api_key(user_id)
        if mode == "cloud":
            self._enforce_cloud_quota(user_id)

        try:
            completion = await self.gateway.complete(
                mode=mode,
                provider=provider,
                api_key=api_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except Exception:
            if mode == "cloud":
                self._record_cloud_usage(user_id, provider, operation, "error")
            raise

        if mode == "cloud":
            self._record_cloud_usage(
                user_id,
                provider,
                operation,
                "success",
                completion.usage_units,
            )
        return completion

    def _enforce_cloud_quota(self, user_id: int) -> None:
        limit = self.settings.cloud_ai_preview_daily_limit
        if limit < 1:
            raise AIRateLimitException("Cloud AI preview is disabled.")
        used = self.usage_repo.count_cloud_requests_since(
            user_id,
            datetime.now(UTC) - timedelta(days=1),
        )
        if used >= limit:
            raise AIRateLimitException("Cloud AI preview daily limit reached.")

    def _record_cloud_usage(
        self,
        user_id: int,
        provider: str,
        operation: str,
        status: str,
        usage_units: int | None = None,
    ) -> None:
        self.usage_repo.create_event(
            user_id=user_id,
            mode="cloud",
            provider=provider,
            operation=operation,
            status=status,
            usage_units=usage_units,
        )
        self.db.commit()

    def _validate_input(self, value: str, field: str) -> str:
        clean_value = str(value or "").strip()
        if not clean_value:
            raise ValidationException(f"{field} is required.")
        if len(clean_value) > self.settings.ai_max_input_chars:
            raise ValidationException(f"{field} is too large for AI processing.")
        return clean_value

    def _validate_git_diff(self, diff: str) -> None:
        lines = diff.splitlines()
        has_diff_header = any(
            line.startswith("diff --git ") or
            line.startswith("--- a/") or
            line.startswith("+++ b/") or
            line.startswith("@@ -")
            for line in lines
        )
        if not has_diff_header:
            raise ValidationException("Invalid git diff format provided.")


def _usage_total(usage: dict[str, Any]) -> int | None:
    for key in ("total_tokens", "totalTokenCount"):
        value = usage.get(key)
        if isinstance(value, int):
            return value
    values = [
        usage.get("input_tokens"),
        usage.get("output_tokens"),
        usage.get("promptTokenCount"),
        usage.get("candidatesTokenCount"),
    ]
    total = sum(value for value in values if isinstance(value, int))
    return total or None


def _changed_files(diff: str) -> list[str]:
    files = []
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                files.append(parts[3].removeprefix("b/"))
        elif line.startswith("+++ b/"):
            files.append(line[6:])
    return list(dict.fromkeys(files))
