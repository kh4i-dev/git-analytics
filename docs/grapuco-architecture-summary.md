# Grapuco Architecture Summary

Source: Grapuco MCP graph for `git-analytics`

Repository ID: `42417d25-9344-4d1f-8f80-d0cf90f9770a`

Status at inspection time: `COMPLETED`

## Grapuco MCP Availability

Grapuco exposed 30 MCP tools. The most relevant tools for architecture work are:

- `list_repositories`
- `search_code`
- `semantic_search`
- `get_dependencies`
- `get_architecture`
- `get_data_flows`
- `get_impact_analysis`
- `get_symbol_context`
- `blast_radius`
- `detect_changes`
- `rename_symbol`
- `check_staleness`
- `detect_tools`
- `grapuco_help`
- `list_skills`
- `get_skill`

Grapuco did not expose MCP resources or resource templates. Calls to `resources/list` and `resources/templates/list` returned `Method not found`.

## Graph Size

- Nodes: `1002`
- Edges: `3098`

Main node types:

- `Function`: `553`
- `File`: `94`
- `Class`: `65`
- `DBModel`: `15`
- `DataFlow`: `200`

Main edge types:

- `STEP_IN_FLOW`
- `CALLS`
- `DEFINES`
- `IMPORTS`
- `STEP_IN_PROCESS`
- `HAS_METHOD`
- `EXTENDS`
- `WRITES_TO_DB`

## Main Modules

The graph confirms a layered FastAPI architecture:

- `app/routes`: HTTP/page/API entrypoints.
- `app/services`: business logic orchestration.
- `app/repositories`: database access layer.
- `app/models`: SQLAlchemy models.
- `app/clients`: external API adapters, especially GitHub.
- `app/core`: config, security, sessions, exceptions, logging.
- `templates`: Jinja dashboard and page UI.
- `migrations`: Alembic schema migrations.
- `tests`: route, service, model, API, and integration coverage.

## Important Files

Highest-centrality files in the Grapuco graph:

- `app/routes/dashboard.py`
- `app/routes/api_analytics.py`
- `app/routes/engineering_reports.py`
- `app/services/analytics_service.py`
- `app/services/sync_service.py`
- `app/clients/github_client.py`
- `app/routes/api_sync.py`
- `app/routes/repositories.py`
- `app/services/engineering_report_service.py`
- `app/routes/auth.py`
- `app/core/session.py`
- `app/repositories/commit_repo.py`
- `app/repositories/repository_repo.py`
- `app/repositories/sync_job_repo.py`
- `app/repositories/pull_request_repo.py`
- `app/repositories/issue_repo.py`

## DB Models

Core persisted models detected by Grapuco:

- `User`: `app/models/user.py`
- `Repository`: `app/models/repository.py`
- `Branch`: `app/models/branch.py`
- `Contributor`: `app/models/contributor.py`
- `Commit`: `app/models/commit.py`
- `PullRequest`: `app/models/pull_request.py`
- `Issue`: `app/models/issue.py`
- `SyncJob`: `app/models/sync_job.py`
- `RepositoryEngineeringReport`: `app/models/engineering_report.py`

Grapuco also labeled some Pydantic request classes as `DBModel`, for example:

- `CreateReportRequest`
- `PublishReportRequest`
- `UpdateReportMetadataRequest`
- `ChangelogRequest`
- `ReleaseNotesRequest`

Treat these as request schemas, not persisted database tables.

## API And Request Flows

Grapuco `get_data_flows` returned function-level traces rather than clean HTTP path traces. The route-to-service-to-repository flow is:

### Repository Import

`app/routes/repositories.py:import_repositories`

Flow:

1. Authenticate user from signed session cookie.
2. Decrypt GitHub token.
3. Call `GitHubClient.list_user_repositories`.
4. Upsert repositories through `RepositoryRepository.upsert_by_user_github_repo_id`.
5. Persist `Repository` rows.

### Manual Repository Sync

`app/routes/repositories.py:sync_repository`

Flow:

1. Authenticate user.
2. Call `SyncService.sync_repository`.
3. `SyncService` calls `GitHubClient`.
4. Data is written through:
   - `BranchRepository`
   - `ContributorRepository`
   - `CommitRepository`
   - `PullRequestRepository`
   - `IssueRepository`
   - `RepositoryRepository`

### Queued Sync API

`app/routes/api_sync.py:enqueue_repository_sync`

Flow:

1. Authenticate user.
2. Validate repository ownership through `RepositoryRepository`.
3. Create queued job through `SyncJobRepository.create_queued`.
4. Enqueue job through `sync_queue`.
5. Worker later runs `SyncService`.

### Analytics API

`app/routes/api_analytics.py`

Flow:

1. Authenticate user.
2. Call `AnalyticsService`.
3. Read through:
   - `RepositoryRepository`
   - `CommitRepository`
   - `PullRequestRepository`
   - `IssueRepository`
   - `ContributorRepository`
4. Return JSON for dashboards/charts/export.

### Insights API

`app/routes/api_insights.py:api_insights`

Flow:

1. Authenticate user.
2. Call `InsightsService`.
3. Read commit, pull request, issue, and repository data.

### Engineering Reports

`app/routes/engineering_reports.py`

Flow:

1. Authenticate user for private report APIs.
2. Use `EngineeringReportService`.
3. Report creation combines:
   - `AnalyticsService`
   - `ReleaseNotesService`
   - `ChangelogService`
   - `RiskInsightService`
4. Persist immutable snapshot through `EngineeringReportRepository`.
5. Public access uses capability URL token through `/r/{public_token}`.

### Tools

Tool routes call matching services:

- Release notes: `ReleaseNotesService` and `ReleaseNotesRepository`
- Changelog: `ChangelogService` and `ChangelogRepository`
- Risk insights: `RiskInsightService` and `RiskRepository`

## Auth Flow

Auth graph centers on:

- `app/routes/auth.py`
- `app/services/auth_service.py`
- `app/core/session.py`
- `app/core/security.py`
- `app/repositories/user_repo.py`

Flow:

1. User opens `/login`.
2. `/auth/github/login` creates signed OAuth state cookie.
3. User is redirected to GitHub OAuth with scopes `repo read:user`.
4. GitHub redirects to `/auth/github/callback` with `code` and `state`.
5. Route validates state query against signed state cookie.
6. `AuthService.authenticate_callback` exchanges code for token.
7. `AuthService` fetches GitHub user profile.
8. Access token is encrypted through `app/core/security.py`.
9. User is upserted through `UserRepository`.
10. App sets signed httpOnly session cookie containing `user_id`.
11. Protected routes parse session cookie through `parse_session_cookie` and load `User` through `UserRepository`.

## High-Risk Files Before Editing

Review these before making changes:

- `app/services/sync_service.py`: GitHub ingestion, DB writes, rollback, sync status.
- `app/services/analytics_service.py`: shared analytics logic for dashboard/API/reports.
- `app/routes/dashboard.py`: many page routes and dashboard state.
- `app/routes/api_analytics.py`: JSON API contract for dashboard/charts/export.
- `app/routes/engineering_reports.py`: private/public report access, publish, revoke, delete.
- `app/services/engineering_report_service.py`: immutable report snapshot generation.
- `app/routes/auth.py`: OAuth and session entrypoints.
- `app/core/session.py`: signed session and OAuth state cookies.
- `app/core/security.py`: GitHub token encryption/decryption.
- `app/repositories/base.py`: shared repository error/write behavior.
- `app/repositories/*_repo.py`: persistence semantics and query assumptions.
- `templates/dashboard_global.html`: global dashboard UI and chart JS.
- `templates/components/executive_analytics.html`: global dashboard component structure.

## Notes

- Grapuco path filtering in `get_data_flows` did not match FastAPI paths directly during inspection. Use function names and symbol context for route-level tracing.
- `get_architecture` is the most useful broad map.
- Use `get_impact_analysis` or `blast_radius` before editing high-risk files.
- Use `detect_changes` after a diff exists to estimate impact before commit.
