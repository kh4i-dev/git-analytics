# Git Analytics — Architecture

---

## Overview

Git Analytics uses a **Layered Architecture (3-layer)** with **Hybrid Routing** (server-rendered pages + JSON API).

```
┌──────────────────────────────────────────────────────────┐
│                    CLIENT (Browser)                       │
├──────────────────────────────────────────────────────────┤
│  Jinja2 Pages          │  JS (fetch → Chart.js)          │
└──────────┬─────────────┴──────────┬───────────────────────┘
           │ page routes             │ API routes
           ▼                         ▼
┌──────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION                     │
├──────────────────────────────────────────────────────────┤
│  ROUTES LAYER                                              │
│  - Page: /dashboard/, /repositories/, /reports/, /tools/  │
│  - API:  /api/v1/analytics/, /api/v1/sync/, /api/v1/reports/ │
│  - Auth: /auth/github/login, /auth/github/callback         │
├──────────────────────────────────────────────────────────┤
│  SERVICE LAYER                                             │
│  - AuthService, SyncService, AnalyticsService              │
│  - EngineeringReportService, ChangelogService              │
│  - ReleaseNotesService, RiskInsightService                 │
│  - SyncQueueService, ExportService                         │
├──────────────────────────────────────────────────────────┤
│  CLIENTS LAYER          │  REPOSITORY LAYER                │
│  - GitHubClient          │  - UserRepo, CommitRepo, PRRepo │
│  - Rate limit parsing    │  - IssueRepo, RepositoryRepo    │
│  - Pagination            │  - ChangelogRepo, ReportRepo    │
│  - Error mapping         │  - RiskRepo, SyncJobRepo        │
├──────────────────────────────────────────────────────────┤
│  DB: SQLAlchemy 2.0 + Alembic migrations                  │
│  SQLite (dev) / PostgreSQL (prod)                          │
└──────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### Layered Architecture
- **Routes** receive HTTP requests, no business logic
- **Services** orchestrate business logic, raise domain exceptions
- **Repositories** persist data, wrap DB errors
- **Clients** talk to external APIs, map HTTP errors to domain exceptions

### Hybrid Routing
- Page routes return Jinja2 HTML (layout + skeleton)
- API routes return JSON (`{ data, error, meta }`)
- Frontend JS fetches API data asynchronously
- Pages have 3 states: loading → data → error

### Single-User Orientation
- One user per deployment
- No workspace/team abstraction
- Manual sync initiation
- Repository-scoped analytics

### DB Snapshot Reports
- Engineering Reports are point-in-time captures
- Analytics state serialized at generation time
- Immutable — does not change after generation

---

## Folder Structure

```
git-analytics/
├── app/
│   ├── main.py                  # App factory, middleware, exception handlers
│   ├── core/
│   │   ├── config.py            # Settings from .env
│   │   ├── security.py          # Token encryption, cookie signing
│   │   ├── exceptions.py        # Domain exception hierarchy
│   │   └── exception_handlers.py # Map domain exceptions → HTTP responses
│   ├── db/
│   │   ├── session.py           # SQLAlchemy engine + session factory
│   │   └── base.py              # DeclarativeBase
│   ├── models/
│   │   ├── user.py, repository.py, contributor.py
│   │   ├── commit.py, pull_request.py, issue.py
│   │   ├── engineering_report.py, sync_job.py
│   ├── repositories/            # Data access layer
│   ├── services/                # Business logic layer
│   ├── clients/                 # External API adapters
│   ├── routes/                  # HTTP endpoints
│   └── schemas/                 # Pydantic request/response models
├── templates/                   # Jinja2 templates
├── migrations/                  # Alembic migrations
├── tests/                       # Test suite
└── docs/                        # Documentation
```

---

## Data Flow: Sync

```
User → Route → SyncService
  1. Pre-check: rate limit, status
  2. Determine mode (full / incremental)
  3. Fetch data via GitHubClient (paginated)
  4. Resolve contributors
  5. Upsert via Repository layer
  6. Update sync status
```

## Data Flow: Analytics

```
User → Dashboard (HTML skeleton)
  → JS fetch → API Route → AnalyticsService
  → Repository layer (SQL aggregation)
  → JSON response → Chart.js render
```

## Data Flow: Report Generation

```
User → Route → EngineeringReportService
  → AnalyticsService (current state)
  → ChangelogService, ReleaseNotesService, RiskInsightService
  → Serialize snapshot to DB
  → Generate PDF/Excel if requested
```

---

## Error Handling

Domain exceptions raised by services are mapped to HTTP status codes by a centralized exception handler. Services never know about HTTP.

| Exception | HTTP Status |
|---|---|
| `RepositoryNotFound` | 404 |
| `GitHubRateLimitExceeded` | 429 |
| `AuthenticationException` | 401 |
| `SyncFailed` | 500 |
| `ConflictException` | 409 |

Standard API response format:
```json
{
  "data": { ... },
  "error": { "code": "...", "message": "..." },
  "meta": { "trace_id": "...", "timestamp": "..." }
}
```
