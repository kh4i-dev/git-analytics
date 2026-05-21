# Release Notes

## Version 1.1.0 (Current)

### Engineering Intelligence Platform

Git Analytics is now positioned as an Engineering Intelligence Platform — a Dev Analytics SaaS and Repository Intelligence Workspace.

#### New Features
- **Engineering Reports**: Immutable snapshots with release notes, changelog, risk insights, and summary metrics
- **Public Report Sharing**: Capability URL access with revoke, token rotation, and anonymization
- **Report Management**: Custom titles, revoke, delete — distinct operations
- **Sync Queue**: Async worker with retry/recovery and `sync_jobs` tracking
- **Branch Analytics**: Multi-branch sync, branch selector, per-branch analytics
- **Executive Overview**: High-level cards for health, velocity, contributors, trends
- **Contributor Profiles**: Per-contributor analytics with commit, PR, issue breakdown
- **Activity Insights**: Streaks, time-of-day, weekday distribution
- **KPI Scoring**: Health gauge (0-100) based on composite metrics

#### AI Workspace
- Commit message generator from staged changes
- PR diff reviewer with code quality analysis
- Repo assistant for natural language Q&A
- Local fallback mode (no API key needed)
- Future hosted provider architecture documented

#### UI/UX
- Dark SaaS theme (GitHub/Vercel/Linear inspired)
- Compact analytics layout with typography-first design
- Responsive tables with horizontal scroll
- Sync status badges with color coding
- Improved login landing page
- AI Workspace conversation layout

#### Export
- PDF export with proper typography
- Excel export for raw data

#### Heatmap
- CSS grid layout for stable rendering
- Responsive overflow with horizontal scroll
- Aligned month labels and tooltips
- Loading/skeleton state

#### Infrastructure
- ADR: 0003-defer-multi-repo-intelligence
- Vietnamese localization support
- CONTEXT.md updated with full domain glossary

## Version 1.0.0

Initial release — Developer Analytics MVP.

- GitHub OAuth authentication
- Repository connection and incremental sync
- Dashboard: Overview, Commits, PRs, Issues
- Developer Insights: heatmap, streaks, activity score
- Ecosystem Explore: GitHub trending, HN, AI tools
- Dark theme (Vercel/Linear inspired)
- REST API with Swagger docs
- Health check endpoint
