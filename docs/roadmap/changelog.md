# Changelog

## [1.2.0] - 2026-05-22

### Added
- Modular AI Tools refactoring splitting `ai_tools.html` into Jinja2 component templates under `templates/ai_tools/`.
- Decoupled client-side static assets (`static/css/ai_tools.css`, `static/js/ai_tools.js`, `static/js/ai_assistant.js`, `static/js/repo_context.js`, `static/js/markdown_renderer.js`).
- Absolute static routing path convention to fix APIRouter static path mapping under Starlette under virtual environments.
- API route `/api/v1/ai/clear-context` to purge conversational cache when repository/branch contexts switch.
- Restructured, clean, and professional multi-level documentation trees under `docs/`.

### Changed
- Dashboard Overview page updated to fully present global cross-repository metrics and aggregation leaderboards.
- Promoted Background Sync Job Queue and Global Aggregation from Phase 4/5 roadmap to Implemented core services.

---

## [1.1.0] - 2025-10-18

### Added
- Engineering report system (immutable snapshots, public sharing, revoke/token rotation).
- Report generation with release notes, changelog, risk insights.
- Public capability URL sharing with anonymization support.
- Report management: custom titles, revoke, delete.
- Sync queue with async worker, retry/recovery, `sync_jobs` table.
- Changelog service and API endpoints.
- Release notes service and API endpoints.
- Risk insight service and API endpoints.
- Branch analytics mode with branch selector.
- Executive overview cards with health score widgets.
- Contributor profile navigation.
- Activity insights (streaks, time-of-day, weekday distribution).
- KPI scoring with health gauge.
- Heatmap improvements (CSS grid, responsive overflow, stable sizing).
- AI Workspace UI with conversation layout.
- PDF export with typography.
- Excel export.
- Vietnamese localization support.

### Changed
- Upgraded UI to SaaS-grade (dark theme, compact layouts, typography-first).
- Dashboard restructured: Overview, Commits, PRs, Issues, Insights pages.
- Sync status badges with color coding.
- Responsive tables with horizontal scroll.
- AnalyticsService: new aggregation queries, improved performance.

### Fixed
- Heatmap infinite auto-stretch, responsive overflow, month alignment, and skeleton states.

---

## [1.0.0] - 2024-06-15

### Added
- GitHub OAuth login/logout.
- Repository connection/disconnection.
- Incremental data sync (commits, PRs, issues).
- Rate limit pre-check before sync.
- Sync status tracking (pending/syncing/success/failed).
- Dashboard Overview with summary cards.
- Dashboard Commits with frequency charts.
- Dashboard Pull Requests with status distribution.
- Dashboard Issues with open/closed charts.
- Developer Insights (heatmap, streaks, scores).
- Ecosystem Explore feed (GitHub trending, HN, AI tools).
- Dark theme (Vercel/Linear inspired).
- API endpoints for all analytics data.
- Swagger API documentation.
- Health check endpoint.

### Security
- Fernet token encryption for GitHub tokens.
- Signed httpOnly session cookies.
- CSRF protection via OAuth state parameter.
- Token never exposed to frontend or logs.
