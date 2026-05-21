# Changelog

## [Unreleased]

### Added
- Engineering report system (immutable snapshots, public sharing, revoke/token rotation)
- Report generation with release notes, changelog, risk insights
- Public capability URL sharing with anonymization support
- Report management: custom titles, revoke, delete
- Sync queue with async worker, retry/recovery, `sync_jobs` table
- Changelog service and API endpoints
- Release notes service and API endpoints
- Risk insight service and API endpoints
- Branch analytics mode with branch selector
- Executive overview cards with health score widgets
- Contributor profile navigation
- Activity insights (streaks, time-of-day, weekday distribution)
- KPI scoring with health gauge
- Heatmap improvements (CSS grid, responsive overflow, stable sizing)
- AI Workspace UI with conversation layout
- PDF export with typography
- Excel export
- Vietnamese localization support
- ADR: 0003-defer-multi-repo-intelligence

### Changed
- Upgraded UI to SaaS-grade (dark theme, compact layouts, typography-first)
- Dashboard restructured: Overview, Commits, PRs, Issues, Insights pages
- Sync status badges with color coding
- Improved login landing page
- Responsive tables with horizontal scroll
- AnalyticsService: new aggregation queries, improved performance

### Fixed
- Heatmap infinite auto-stretch
- Heatmap responsive overflow
- Heatmap grid sizing stability
- Month label alignment
- Cell spacing on small viewports
- Loading/skeleton state for charts

## [1.0.0] - 2024-06-15

### Added
- GitHub OAuth login/logout
- Repository connection/disconnection
- Incremental data sync (commits, PRs, issues)
- Rate limit pre-check before sync
- Sync status tracking (pending/syncing/success/failed)
- Dashboard Overview with summary cards
- Dashboard Commits with frequency charts
- Dashboard Pull Requests with status distribution
- Dashboard Issues with open/closed charts
- Developer Insights (heatmap, streaks, scores)
- Ecosystem Explore feed (GitHub trending, HN, AI tools)
- Dark theme (Vercel/Linear inspired)
- API endpoints for all analytics data
- Swagger API documentation
- Health check endpoint

### Security
- Fernet token encryption for GitHub tokens
- Signed httpOnly session cookies
- CSRF protection via OAuth state parameter
- Token never exposed to frontend or logs
