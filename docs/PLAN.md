
# Major Web Improvement Plan

## 1. Current System Summary

Baseline sources:
- [grapuco-architecture-summary.md](E:/my-project/git-analytics/docs/grapuco-architecture-summary.md)
- [CONTEXT.md](E:/my-project/git-analytics/CONTEXT.md)
- ADRs under [docs/adr](E:/my-project/git-analytics/docs/adr)
- Grapuco targeted `semantic_search`, `search_code`, `check_staleness`, and `blast_radius`

Current architecture:
- Hybrid FastAPI app: Jinja page routes plus JSON APIs with response shape `{ data, error, meta }`.
- Main layers are already clear: `routes -> services -> repositories -> SQLAlchemy models/migrations`.
- Frontend is template-driven with Chart.js and significant inline CSS/JS in page templates and shared dashboard layout.
- Main persisted domain models include `User`, `Repository`, `Contributor`, `Commit`, `PullRequest`, `Issue`, `Branch`, `SyncJob`, `RepositoryEngineeringReport`, and `AiProviderSetting`.

Current auth/session flow:
- GitHub OAuth starts in [auth.py](E:/my-project/git-analytics/app/routes/auth.py).
- `AuthService` exchanges code for token and stores encrypted GitHub token in DB.
- Browser receives signed `httpOnly` session cookie containing `user_id`.
- Many routes parse session cookies through duplicated route-local auth helpers.

Current data flows:
- Sync: GitHub client -> `SyncService` -> repository upserts -> sync status/jobs.
- Analytics: raw synced tables -> `AnalyticsService` aggregations -> dashboard/API/templates.
- Reports: synced DB snapshot -> `EngineeringReportService` -> immutable report/public capability link.
- AI: Settings persistence already exists with encrypted BYOK rows and Cloud env detection, but AI tool execution in [api_ai.py](E:/my-project/git-analytics/app/routes/api_ai.py) is still rule-based/heuristic rather than real provider abstraction.

Grapuco findings:
- Graph is stale versus current `HEAD`; `check_staleness` recommends full refresh before high-risk implementation.
- `parse_session_cookie` has HIGH blast radius across dashboard, sync, reports, tools, and API routes.
- `AnalyticsService.get_global_overview` has MEDIUM blast radius on global dashboard/export.
- Settings page itself is lower risk, but it depends on shared auth and dashboard layout.

## 2. Problems Found

| Area | Problems |
|---|---|
| UX | Settings copy is stale about BYOK storage; template-local CSS/JS makes polish inconsistent; loading/error/empty/mobile/accessibility behavior varies across dashboard, reports, repositories, and AI tools. |
| Architecture | Shared UI layout and large route/service files create wide edit impact; auth logic is repeated per route; AI settings persistence is ahead of AI execution architecture. |
| AI | No real provider-call abstraction yet; Cloud AI and OpenAI-compatible gateway need a server-side execution seam; docs still mention Local Fallback/local AI product direction. |
| Security | Production config needs explicit validation for secret/session/encryption settings; CSRF posture for state-changing cookie-auth routes needs review; Cloud AI needs quota/rate-limit controls. |
| Data | Contributor identity limitations are documented; branch filtering and multi-branch commit representation need reliability/performance review before analytics expansion. |
| Production | Trace IDs and JSON logging exist, but CI/lint/typecheck gates are not evident; provider observability, rollback flags, and visual regression baselines are weak. |

## 3. Improvement Options

| Direction | Scope | Tradeoff |
|---|---|---|
| Conservative | UI cleanup, stale docs/copy fixes, baseline tests, limited accessibility/responsive work | Lowest risk, but leaves AI execution and production gaps unresolved |
| Balanced | UI polish + AI execution architecture + backend hardening + analytics reliability checks + hosted-preview readiness | Best leverage without rewriting the app |
| Ambitious | Frontend restructuring, broader worker/identity/billing architecture, deeper analytics redesign | High risk and drifts toward deferred multi-repo/platform work |

## 4. Recommended Direction

Choose **Balanced**.

Reason:
- It fixes visible product quality issues first.
- It completes the AI architecture already started by encrypted BYOK settings.
- It respects current FastAPI/Jinja/service/repository style.
- It avoids violating ADR constraints around deferred multi-repo intelligence and expensive GitHub detail sync.

Locked product defaults:
- Release target: **Hosted preview**.
- OpenClaw/OpenAI-compatible support: **server-side Cloud AI adapter**, not a BYOK custom-provider UI.
- Keep canonical UI provider choices stable: OpenAI, Gemini, Claude.
- Do not reintroduce Local Workspace or Local Fallback AI mode.

Interface decisions:
- Preserve current public API shape `{ data, error, meta }`.
- Keep AI Settings endpoints stable unless a typed request model replaces raw parsing without changing wire shape.
- Add an internal AI provider execution seam for commit generation, review, and assistant operations.
- Map OpenAI-compatible gateway configuration through server config behind Cloud AI, not through browser-stored secrets.

## 5. Phased Plan

| Phase | Objective and affected modules | Backend / Frontend / DB | Security, tests, verification, rollback |
|---|---|---|---|
| Phase 0 | Establish safe baseline around Settings, dashboards, repositories, reports, AI, auth, sync | Refresh Grapuco graph; capture desktop/mobile screenshots; record current API contracts and migration head | Run baseline tests and migration checks; stop if graph or test baseline is unstable |
| Phase 1 | UI/UX cleanup in Settings, dashboard/global overview, repository overview, AI tools, reports, sidebar states | Frontend-first template cleanup in page-local templates before shared layout edits; backend only for page context/state fixes; no DB change | Preserve secret masking; add route render/state tests; verify responsive/error/empty/loading states; rollback by reverting isolated template changes |
| Phase 2 | Finish AI Settings and AI execution architecture | Backend provider seam, BYOK/cloud execution path, Cloud gateway adapter, quota hook; frontend Settings/AI Tools states; DB add preview-safe usage tracking if Cloud AI enabled | Never expose raw keys; provider errors wrapped/redacted; test key masking, cloud availability, gateway config, limits; rollback via Cloud AI disable flag/env |
| Phase 3 | Harden API/service/repository seams | Consolidate auth dependency pattern carefully, strengthen request validation, normalize async error handling and trace-aware responses | High-risk auth blast radius; add route/service regression tests; no DB unless required; rollback in small route groups |
| Phase 4 | Improve analytics/report reliability | Audit sync idempotency, contributor/branch mapping, query plans, report stale-state handling; UI warnings for reliability states | Migration-first only for confirmed indexes; test duplicate sync, incremental sync, stale jobs, report immutability; rollback additive indexes and keep snapshots stable |
| Phase 5 | Hosted-preview readiness | Env validation, cookie/session/CSRF review, CI checks, observability, provider quotas, deployment/rollback docs | Add security smoke tests and release checklist; rollback through env flags, migrations downgrade plan, and feature-disable path |

## 6. File Impact Map

| Risk | Likely modules/files | Why |
|---|---|---|
| High | [session.py](E:/my-project/git-analytics/app/core/session.py), [auth.py](E:/my-project/git-analytics/app/routes/auth.py), [security.py](E:/my-project/git-analytics/app/core/security.py) | Auth/session/encryption touch most protected flows |
| High | [dashboard_base.html](E:/my-project/git-analytics/templates/layouts/dashboard_base.html), dashboard sidebar/topbar templates | Shared navigation/layout affects most pages |
| High | [analytics_service.py](E:/my-project/git-analytics/app/services/analytics_service.py), [sync_service.py](E:/my-project/git-analytics/app/services/sync_service.py), [sync_queue.py](E:/my-project/git-analytics/app/services/sync_queue.py) | Core data and dashboard reliability |
| Medium | [settings.html](E:/my-project/git-analytics/templates/settings.html), [ai_tools.html](E:/my-project/git-analytics/templates/ai_tools.html), [api_ai.py](E:/my-project/git-analytics/app/routes/api_ai.py) | AI UX and execution path |
| Medium | AI settings route/service/repository/model modules | Existing encrypted BYOK/Cloud state must stay backward compatible |
| Medium | Reports route/service/template modules | Public report sharing and snapshot correctness |
| Low-Medium | Repository and page-local dashboard templates | Visible UX changes but narrower behavior impact if kept local |

## 7. DB/Migration Plan

- Keep existing `ai_provider_settings` table and migration as the AI settings source of truth.
- Add a migration for **Cloud AI preview usage tracking** if Cloud requests are enabled for hosted preview:
  - suggested table: `ai_usage_events`
  - store user, mode, provider, operation, status, timestamps, coarse token/count metadata if available
  - do not store prompts, diffs, API keys, or raw provider secrets
  - indexes on `(user_id, created_at)` and `(provider, created_at)`
- Do not add OpenClaw BYOK schema for this plan; gateway config stays server-side.
- Analytics/report migrations should be additive index migrations only after query-plan evidence.
- No contributor identity redesign or multi-repo schema expansion in this improvement cycle.

## 8. Security Plan

- Require production-safe `SECRET_KEY` and `ENCRYPTION_KEY`; reject unsafe defaults for hosted preview.
- Keep GitHub tokens and BYOK keys encrypted server-side; decrypt only inside execution paths.
- Keep Cloud AI and OpenAI-compatible gateway secrets in server ENV only.
- Do not expose secrets via `NEXT_PUBLIC_*`, client logs, API responses, templates, or localStorage.
- Validate provider, mode, AI input size, report payloads, and all route parameters server-side.
- Add per-user Cloud AI rate limits and preview quotas before enabling hosted Cloud AI broadly.
- Preserve trace IDs and structured logging while redacting secrets, diffs, prompts, and provider auth headers.
- Review cookie auth state-changing routes for CSRF posture and session cookie production flags.

## 9. Test Plan

- Unit tests:
  - provider selection, gateway adapter routing, masking/redaction, quota decisions
  - sync mapping/idempotency helpers
  - analytics/report service edge cases
- Route tests:
  - Settings AI GET/PUT/DELETE contracts
  - protected routes and session failures
  - AI disabled/cloud unavailable/provider error responses
- Migration tests:
  - Alembic head remains linear
  - upgrade/downgrade for any new usage/index migration
- UI smoke tests:
  - Settings, global dashboard, repository overview, AI tools, reports
  - empty/loading/error states
  - desktop and mobile layout checks
  - keyboard/focus/label checks for settings and navigation
- Current baseline commands:
  - `.venv\Scripts\python.exe -m pytest -q` -> `100 passed`
  - `.venv\Scripts\python.exe -m alembic heads` -> `f3a1b2c4d5e6 (head)`

## 10. Implementation Order

1. Refresh Grapuco index and lock baseline screenshots/tests.
2. Phase 1 UI cleanup on narrow templates before shared dashboard layout.
3. Phase 2 AI execution seam and Cloud gateway support with quota/security controls.
4. Phase 3 route/auth/validation hardening after AI contracts are stable.
5. Phase 4 sync/analytics/report reliability work after profiling and data fixtures are ready.
6. Phase 5 CI/env/security/observability release gates.

## 11. Stop Conditions

Stop and ask before continuing if:
- A phase requires a schema change beyond approved migration scope.
- A high-risk file has wider Grapuco impact than expected after graph refresh.
- Any change risks exposing API keys, GitHub tokens, prompts, or provider ENV values.
- Auth/session hardening changes cookie semantics or breaks OAuth assumptions.
- Analytics fixes require deferred multi-repo identity/platform work.
- Cloud AI quota strategy needs billing/product rules not yet approved.
- Shared layout edits risk unrelated dashboard pages without a visual regression baseline.
- The requested work moves beyond the specifically approved phase.

