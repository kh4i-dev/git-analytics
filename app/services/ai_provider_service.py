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
        raise ValidationException("Invalid AI provider.")

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

    async def generate_commit_message(self, *, user_id: int, diff: str) -> dict[str, Any]:
        clean_diff = self._validate_input(diff, "diff")
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
        return {"message": message[:240], "files": _changed_files(clean_diff)[:12]}

    async def review_diff(self, *, user_id: int, diff: str) -> dict[str, Any]:
        clean_diff = self._validate_input(diff, "diff")
        completion = await self._complete(
            user_id=user_id,
            operation="pr_review",
            system_prompt=(
                "Review the provided pull request diff for correctness, security, "
                "reliability, and missing tests. Return concise plain text."
            ),
            user_prompt=clean_diff,
        )
        return {
            "findings": [
                {
                    "type": "provider",
                    "title": "Provider review",
                    "detail": completion.text[:5000],
                }
            ],
            "files": _changed_files(clean_diff)[:12],
        }

    async def answer_question(self, *, user_id: int, question: str) -> dict[str, str]:
        clean_question = self._validate_input(question, "question")
        completion = await self._complete(
            user_id=user_id,
            operation="repo_assistant",
            system_prompt=(
                "Answer repository engineering questions only from context the user provides. "
                "Say when additional repository context is needed."
            ),
            user_prompt=clean_question,
        )
        return {"answer": completion.text[:8000], "mode": "configured_provider"}

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
