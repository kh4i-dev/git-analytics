# Git Analytics — Domain Glossary

## Core Entities

- **User**: An individual who authenticates via GitHub OAuth. Owns the session and selects repositories to analyze. In MVP, this is always an Individual Developer.

- **Repository**: A GitHub repository that a User connects to the system for analysis. Belongs to a User's GitHub account (or an org they have access to). Data is synced from GitHub REST API.

- **Contributor**: A person who has contributed to a Repository (commits, PRs, issues). A Contributor is NOT necessarily a User in the system — they are extracted from GitHub data. One User may also appear as a Contributor in their own repos. Identity is resolved by: `github_login` (preferred) with fallback to `email`. A `source_type` field distinguishes `github_user` from `git_email`. Known limitation in MVP: the same person using multiple emails may appear as separate Contributors.

- **Commit**: A single git commit within a Repository. Attributed to a Contributor. Contains metadata: message, timestamp, additions, deletions.

- **Pull Request**: A GitHub pull request within a Repository. Has a state (open, closed, merged), author (Contributor), reviewers, timestamps.

- **Issue**: A GitHub issue within a Repository. Has a state (open, closed), author, labels (stored as JSON array), timestamps. Label-based analytics computed at application level in Python, not via SQL joins.

## Future Entities (NOT in MVP)

- **Team**: A group of Contributors managed by a Team Lead. Deferred to post-MVP.
- **Organization**: A GitHub org. Deferred to post-MVP.
- **Membership / Role**: Relationship between User and Team. Deferred to post-MVP.

## Product Direction

- **Personal Developer Utility**: The primary product direction for the current roadmap; a tool for an Individual Developer to turn repository activity into useful personal outputs.

- **Team Engineering Intelligence**: A later product direction for team and organization workflows. Avoid treating "workspace", "team", or "org" as current-domain concepts until Team, Organization, and Membership / Role are introduced.

- **Active Product Phases**: The current implementation roadmap covers Phase 1 Engineering Toolkit, Phase 2 Single-Repo AI Insight Engine, and Phase 3 Hosted/SaaS Foundation.

- **Future Operating System Update**: The deferred roadmap update for multi-repo intelligence, workspace-level reports, cross-repo contributor ranking, executive overview, and identity resolution.

- **Engineering Report**: A shareable snapshot of repository activity for an Individual Developer, combining release notes, changelog, risk insights, and summary context into one canonical report object.

- **As-of Date**: The visible timestamp that tells a report reader when the Engineering Report was generated and which synced dataset it is based on.

- **Report Generation**: Creating an Engineering Report from repository data already synced into the local database; it does not fetch new GitHub data.

- **Stale Data Threshold**: The configurable age after which synced repository data should be treated as stale for report-generation warnings.

- **Report Date Range**: The stored period that an Engineering Report covers, with explicit `from_date` and `to_date` values visible to report readers.

- **Continuity Range**: The default report date range that starts after the previous report for the same Repository; for the first report, it falls back to the shorter of first sync date or the default lookback window.

- **Risk Insight Snapshot**: Risk insight data serialized into an Engineering Report at generation time so the shared report remains stable when viewed later.

- **Generated Report Title**: The automatic title assigned when an Engineering Report is created, usually derived from repository name and Report Date Range.

- **Custom Report Title**: An optional user-edited display title for an Engineering Report; when absent, readers see the Generated Report Title.

- **Public Link Revocation**: Removing public access to an Engineering Report without deleting the private report from the owner's dashboard.

- **Public Report Anonymization**: A report-level setting that hides the Repository's real `full_name` in the public view and replaces it with a snapshot display name, without changing the Repository itself.

- **Public Report Name**: The repository name shown to anonymous readers of a public Engineering Report; by default it is the Repository `full_name`, but anonymized reports show the configured public display name or "Private Repository".

- **Report Deletion**: Permanently removing an Engineering Report from the owner's dashboard; distinct from Public Link Revocation.

- **Public Report Not Found**: The public response for invalid or revoked report tokens; public routes return 404 to avoid revealing whether a token ever existed.

- **Public Report Token Rotation**: Publishing a report after revocation creates a new public token; revoked tokens are never reused.

- **Non-indexed Public Report**: A public Engineering Report shared by capability URL that should not be indexed or followed by search engines in Phase 1.

- **Capability URL Access**: The Phase 1 public sharing model where possession of a long random public report URL grants anonymous read access to that immutable report snapshot.

- **No Public Report Password**: Phase 1 public Engineering Reports do not use passwords or passcodes; access is controlled through Capability URL Access, Public Link Revocation, and Public Report Token Rotation.

- **Future Report Access Control**: Later access-control options for shared reports, such as allowed email/domain, signed invite links, expiring links, and team permission models.

- **Non-expiring Public Report Link**: The Phase 1 default where a public report link remains valid until the owner revokes it or deletes the report.

## Relationships

- A **User** owns one or more **Engineering Reports**.
- An **Engineering Report** belongs to exactly one **Repository** in Phase 1.
- An **Engineering Report** has one **Generated Report Title** and may have one **Custom Report Title**.
- An **Engineering Report** has one **Report Date Range** and one **As-of Date**.
- **Public Link Revocation** affects anonymous access only; the owner can still access the **Engineering Report** privately.
- **Public Report Anonymization** affects only the public report snapshot; the owner dashboard still shows the real **Repository** name.
- A revoked or invalid public report token produces **Public Report Not Found**.
- **Public Report Token Rotation** ensures a revoked public link cannot regain access after republishing.
- A **Non-indexed Public Report** is shareable by URL but is not treated as a public portfolio page.
- **Capability URL Access** applies only to the immutable public snapshot; the private report record still belongs to the owner **User**.
- **No Public Report Password** keeps Phase 1 sharing separate from **Future Report Access Control**.
- A **Non-expiring Public Report Link** can be invalidated by **Public Link Revocation** or **Report Deletion**.
- **Future Operating System Update** depends on sync, job-status, rate-limit, and contributor-identity foundations that are not part of Phase 1-3.

## Flagged Ambiguities

- "revoke" does not mean "delete"; revoking a public link removes public access but keeps the private report.
- "title" splits into **Generated Report Title** and **Custom Report Title**; editing the display title must not overwrite the generated title.
- "anonymize repository" means anonymize the **Engineering Report** public view, not mutate the **Repository**.
- Revoked public links return 404, not 410, so anonymous readers cannot distinguish revoked links from invalid tokens.
- Republish after revoke creates a new public token; the old token remains invalid.
- Public report pages are `noindex, nofollow` in Phase 1; SEO/portfolio publishing is a separate future mode.
- Phase 1 public reports do not require a password or passcode.
- Higher-control sharing belongs to **Future Report Access Control**, not the Phase 1 capability URL model.
- Phase 1 public report links do not expire by default; expiring links are a future access-control option.
- Multi-repo intelligence and workspace-level KPIs belong to **Future Operating System Update**, not the active Phase 1-3 roadmap.

## Key Distinctions

- **Sync**: Pulling data from GitHub REST API into the local database. User-initiated (button press), not a background process (in MVP). Uses **Incremental Sync** strategy: first sync is full, subsequent syncs use `since=last_synced_at` to fetch only new data.

- **Full Sync**: Fetching all historical data for a Repository. Triggered when `last_synced_at` is null (first time).

- **Incremental Sync**: Fetching only data created/updated after `last_synced_at`. Reduces API calls and respects GitHub rate limits.

- **Sync Status**: Each Repository tracks `last_synced_at`, `last_sync_status`, and `last_sync_error`. On success, `last_synced_at` is updated. On failure, it is NOT updated — ensuring the next sync retries from the same point.

- **Rate Limit Check**: A pre-sync call to `GET /rate_limit` to inspect remaining API quota before starting a sync. If quota is too low, the system warns the user instead of proceeding.

- **Rate Limit Failure**: When GitHub returns HTTP 403 during sync. The sync halts immediately, `last_sync_status` is set to "failed", `last_sync_error` records the reason, and `last_synced_at` is NOT updated — making the next retry safe.

- **GitHub OAuth**: Authentication mechanism using GitHub OAuth App with `repo` + `read:user` scopes. Grants read access to both public and private repositories. The `repo` scope technically includes write permissions, but the system enforces **read-only in business logic** — no write endpoints are ever called.

- **Access Token**: The OAuth token obtained after GitHub login. Encrypted and stored in `users.encrypted_github_token`. Never exposed to frontend. Client receives only a signed httpOnly cookie containing `user_id`. Token is decrypted server-side only when calling GitHub API. Token must not appear in logs. All secrets (`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, encryption key) live in `.env`.

- **SyncService**: Orchestrates the sync workflow. Decides full vs incremental sync, calls GitHubClient for data, calls Repository layer to persist, and updates sync status fields. Does not know HTTP details.

- **GitHubClient**: Adapter that encapsulates all GitHub REST API communication. Handles: auth headers, base URL, pagination (`per_page=100`), rate limit header parsing, and HTTP error-to-domain-error mapping. The only component that imports `httpx`.

- **Repository Layer**: Data access layer that persists entities (commits, PRs, issues, contributors) to the database. Uses upsert to avoid duplicates. Wraps database errors.

- **AnalyticsService**: Serves dashboard data by running SQL aggregation queries through the Repository layer. Computes on read from raw tables — not pre-aggregated (in MVP).

- **Dashboard**: Multi-page analytics UI with 4 pages: Overview (summary cards + key charts), Commits (frequency, by contributor), Pull Requests (status, merge time), Issues (open/closed, by label). Each page loads only its own data. Rendered via Jinja2 + Chart.js.

- **Domain Exception**: Business-logic errors raised by Service layer. Never HTTPException — services do not know about HTTP. Mapped to HTTP status codes by a centralized exception handler. Examples: `RepositoryNotFound` → 404, `GitHubRateLimitExceeded` → 429, `SyncFailed` → 500.

- **API Response Format**: Standardized JSON structure: `{ data, error: { code, message }, meta: { trace_id, timestamp } }`. All responses — success and error — follow this format for consistency.

- **Hybrid Routing**: Two sets of routes coexist. Page routes (`/dashboard/*`) return Jinja2 HTML (layout + skeleton). API routes (`/api/v1/*`) return JSON data. Frontend JS calls API routes via fetch to populate Chart.js. Pages show loading → data → or error state.
