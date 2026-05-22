# Release Notes

## Version 1.2.0 (Current)

### Modular AI Workspace & Nested Docs Refactoring
This release introduces a major architectural improvements to the AI Tools suite, moving from a monolithic Jinja layout into clean decoupled sub-components and modular JavaScript ES6 libraries, as well as reorganizing and aligning the entire codebase documentation.

#### Key Architectural Changes
* **Modular Jinja Components**: Decoupled `templates/ai_tools.html` into independent files under `templates/ai_tools/` for easy maintainability (e.g. `_workspace_header.html`, `_repo_selector.html`, `_repo_assistant.html`, `_provider_settings.html`).
* **Client-Side ES6 Separation**: Isolated JavaScript code into standalone static modules (`static/js/ai_tools.js`, `repo_context.js`, `ai_assistant.js`, `markdown_renderer.js`).
* **FastAPI Static Route Resolution**: Solved path-matching route discrepancies by transitioning to absolute client-side assets routing `/static/...` instead of sub-router `url_for` lookups.
* **Purge Conversation Cache**: Added a POST handler at `/api/v1/ai/clear-context` to safely discard in-memory context caches when users toggle repositories or branch filters, preventing cross-context leakages.
* **Professional Nested Documentation**: Relocated and consolidated all early architecture design logs, Vietnamese translations, specifications, and SVG schemas into a professional, multi-level directory tree under `docs/`.

---

## Version 1.1.0

### Engineering Intelligence Platform
Git Analytics is now positioned as a comprehensive Engineering Intelligence Platform — a Dev Analytics SaaS and Repository Intelligence Workspace.

#### New Features
- **Engineering Reports**: Immutable snapshots with release notes, changelog, risk insights, and summary metrics.
- **Public Report Sharing**: Capability URL access with revoke, token rotation, and anonymization.
- **Report Management**: Custom titles, revoke, delete — distinct operations.
- **Sync Queue**: Async worker with retry/recovery and `sync_jobs` tracking.
- **Branch Analytics**: Multi-branch sync, branch selector, per-branch analytics.
- **Executive Overview**: High-level cards for health, velocity, contributors, trends.
- **Contributor Profiles**: Per-contributor analytics with commit, PR, issue breakdown.
- **Activity Insights**: Streaks, time-of-day, weekday distribution.
- **KPI Scoring**: Health gauge (0-100) based on composite metrics.

#### AI Workspace
- Commit message generator from staged changes.
- PR diff reviewer with code quality analysis.
- Repo assistant for natural language Q&A.
- Local fallback mode (no API key needed).
- Future hosted provider architecture documented.

#### UI/UX
- Dark SaaS theme (GitHub/Vercel/Linear inspired).
- Compact analytics layout with typography-first design.
- Responsive tables with horizontal scroll.
- Sync status badges with color coding.
- Improved login landing page.
- AI Workspace conversation layout.

#### Export
- PDF export with proper typography.
- Excel export for raw data.

#### Heatmap
- CSS grid layout for stable rendering.
- Responsive overflow with horizontal scroll.
- Aligned month labels and tooltips.
- Loading/skeleton state.

#### Infrastructure
- ADR: 0003-defer-multi-repo-intelligence.
- Vietnamese localization support.
- CONTEXT.md updated with full domain glossary.

---

## Version 1.0.0

Initial release — Developer Analytics MVP.

- GitHub OAuth authentication.
- Repository connection and incremental sync.
- Dashboard: Overview, Commits, PRs, Issues.
- Developer Insights: heatmap, streaks, activity score.
- Ecosystem Explore: GitHub trending, HN, AI tools.
- Dark theme (Vercel/Linear inspired).
- REST API with Swagger docs.
- Health check endpoint.
