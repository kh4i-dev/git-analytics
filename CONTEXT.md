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
