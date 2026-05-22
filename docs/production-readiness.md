# Hosted Preview Readiness

## Secrets and sessions

- Set `APP_ENV=production`, `DEBUG=false`, a non-placeholder `SECRET_KEY`, and a Fernet `ENCRYPTION_KEY`.
- Keep GitHub OAuth secrets, Cloud AI keys, and OpenAI-compatible gateway keys in server ENV or a secret manager.
- Browser session cookies remain signed, `httpOnly`, `SameSite=Lax`, and `Secure` in production.
- State-changing cookie-auth routes must stay same-origin in deployed ingress policy; add CSRF tokens before allowing cross-origin browser mutations.

## AI preview

- BYOK keys are encrypted in `ai_provider_settings` and are never returned raw to the Settings UI.
- Cloud AI is preview-only until billing and quota policy is finalized.
- Cloud usage events store provider, operation, status, and coarse usage units only. Do not store prompts, diffs, raw responses, or secrets.
- Set `CLOUD_AI_PREVIEW_DAILY_LIMIT` conservatively and disable Cloud mode by removing server provider credentials when rolling back.

## Release checks

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall app tests
.venv\Scripts\python.exe -m alembic heads
```

Run `alembic upgrade head` in a migration window before enabling Cloud AI on a hosted database. Roll back Cloud AI first through ENV, then downgrade the additive usage migration if the table must be removed.
