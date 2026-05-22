# Git Analytics — Architecture & Hosted Readiness Guide

This document describes the design principles, structural layering, data flows, and hosting readiness checklist for the Git Analytics platform.

---

## 1. Architectural Design & Overview

Git Analytics uses a **Layered Architecture (3-layer)** with **Hybrid Routing** (server-rendered pages + JSON API).

```
┌──────────────────────────────────────────────────────────┐
│                    CLIENT (Browser)                      │
├──────────────────────────────────────────────────────────┤
│  Jinja2 Pages          │  JS (fetch → Chart.js)          │
└──────────┬─────────────┴──────────┬───────────────────────┘
           │ page routes             │ API routes
           ▼                         ▼
┌──────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION                   │
├──────────────────────────────────────────────────────────┤
│  ROUTES LAYER                                            │
│  - Page: /dashboard/, /repositories/, /reports/, /tools/  │
│  - API:  /api/v1/analytics/, /api/v1/sync/, /api/v1/reports/ │
│  - Auth: /auth/github/login, /auth/github/callback         │
├──────────────────────────────────────────────────────────┤
│  SERVICE LAYER                                           │
│  - AuthService, SyncService, AnalyticsService            │
│  - EngineeringReportService, ChangelogService            │
│  - ReleaseNotesService, RiskInsightService               │
│  - SyncQueueService, ExportService, AIProviderService    │
├──────────────────────────────────────────────────────────┤
│  CLIENTS LAYER          │  REPOSITORY LAYER              │
│  - GitHubClient          │  - UserRepo, CommitRepo, PRRepo│
│  - Rate limit parsing    │  - IssueRepo, RepositoryRepo   │
│  - Pagination            │  - ChangelogRepo, ReportRepo   │
│  - Error mapping         │  - RiskRepo, SyncJobRepo       │
├──────────────────────────────────────────────────────────┤
│  DB: SQLAlchemy 2.0 + Alembic migrations                 │
│  SQLite (dev) / PostgreSQL (prod)                        │
└──────────────────────────────────────────────────────────┘
```

### Key Design Decisions

* **Layered Architecture**:
  * **Routes** receive HTTP requests and manage session flow, containing zero business logic.
  * **Services** orchestrate business logic, handle computational logic (e.g. streaks, metrics calculations), and raise domain exceptions.
  * **Repositories** perform data persistence and querying via SQLAlchemy, wrapping database-specific errors.
  * **Clients** communicate with external APIs (e.g., GitHub API, AI Provider Gateways) and translate network/HTTP errors into domain-specific exceptions.
* **Hybrid Routing**:
  * Page routes return server-rendered Jinja2 HTML layouts with initial structural templates.
  * API routes return clean, standard JSON responses (`{ "data": ..., "error": ..., "meta": ... }`).
  * Frontend vanilla JavaScript fetches API data asynchronously, enabling interactive widgets and smooth charts using Chart.js without full-page reloads.
  * Dynamic interfaces have explicit states: Loading, Active Data, and Error.
* **Single-User / Multi-Repository Analytics**:
  * Single-user login via GitHub OAuth, securing the dashboard for solo developers/managers.
  * Multi-repository data synchronization, offering both single-repository analytics and global cross-repository KPI dashboards.
  * Background synchronization queues with multi-repo parallel task management and automated retries.
* **DB Snapshot Reports**:
  * Engineering Reports are immutable, point-in-time captures of analytics data.
  * Once generated, the analytical metrics, changelogs, release notes, and risk insights are serialized to the database, ensuring historical records remain unaltered even if source repositories change.

---

## 2. Directory Layout & Structure

```
git-analytics/
├── app/
│   ├── main.py                  # FastAPI App factory, middleware, static files, exceptions
│   ├── core/
│   │   ├── config.py            # Pydantic Settings loaded from ENV/.env
│   │   ├── security.py          # Cookie signing, credential encryption/decryption
│   │   ├── exceptions.py        # Centralized domain-exception hierarchy
│   │   └── exception_handlers.py # Decoupled routers mapping exceptions to HTTP
│   ├── db/
│   │   ├── session.py           # SQLAlchemy database engines & session makers
│   │   └── base.py              # Central DeclarativeBase for models
│   ├── models/                  # Database models (User, Repo, Commit, PR, Issue, etc.)
│   ├── repositories/            # Decoupled DB query layer
│   ├── services/                # Cohesive core services (Sync, Analytics, AI, Reports)
│   ├── clients/                 # Outbound clients (GitHub client, AI providers)
│   ├── routes/                  # Modular APIRouters (auth, dashboard, explore, API v1)
│   └── schemas/                 # Pydantic serialization and validation schemas
├── static/                      # Static assets (CSS, JS libraries, Chart.js, etc.)
│   ├── css/                     # Sleek dark SaaS theme styles (e.g. ai_tools.css)
│   └── js/                      # Decoupled ES6 modules (e.g. ai_tools.js, markdown_renderer.js)
├── templates/                   # Jinja2 HTML templates
│   ├── ai_tools/                # Component-based modular sub-templates
│   └── partials/                # Reusable layouts, cards, and modal components
├── migrations/                  # Alembic DB migration files
├── tests/                       # Complete pytest suite (115+ unit/integration tests)
└── docs/                        # Restructured modular documentation tree
```

---

## 3. Core Technical Data Flows

### A. Repository Synchronisation Flow
```
User (Browser UI) ──► Route ──► SyncService
                                    │
    ┌───────────────────────────────┴────────────────────────────────┐
    ▼ (Pre-checks)                                                   ▼ (Data Retrieval)
Check active state & rate limit                                Fetch branches/commits/PRs/issues
                                                               via paginated GitHubClient
                                                                     │
    ┌───────────────────────────────┬────────────────────────────────┘
    ▼ (Resolution)                  ▼ (Persistence)
Resolve user identities         Bulk upsert via Repository layers
to central Contributors         Update SyncJob queue status
```

### B. Asynchronous Frontend Data Fetching
```
User (Browser) ──► Hits Page Route ──► Returns Jinja2 HTML Layout skeleton
     │
     ▼ (On Load)
JavaScript Fetch ──► Calls API Route ──► AnalyticsService (aggregates data)
     │                                            │
     ▼ (Renders)                                  ▼
Chart.js components ◄────────────────────── Returns JSON payload
```

### C. Snapshot Report Generation
```
User ──► Report Route ──► EngineeringReportService
                               │
       ┌───────────────────────┼────────────────────────┐
       ▼                       ▼                        ▼
AnalyticsService        ChangelogService        ReleaseNotesService
(captures metrics)     (compiles changes)      (summarizes features)
       │                       │                        │
       └───────────────────────┼────────────────────────┘
                               ▼
                    Serialize snapshot to DB
                               │
            ┌──────────────────┴──────────────────┐
            ▼ (Optional)                          ▼ (Optional)
      ExportService (PDF)                  ExportService (Excel)
```

---

## 4. Hosted Preview & Production Readiness

Ensure the following configuration guidelines are implemented prior to deploying Git Analytics to a public or production environment.

### Secrets and Session Management
* Set `APP_ENV=production` and `DEBUG=false` in the environment.
* Change `SECRET_KEY` and `ENCRYPTION_KEY` (used for encrypting BYOK tokens) from developer defaults to cryptographically secure keys (e.g., generated using `openssl rand -hex 32`).
* Browser session cookies remain signed, `httpOnly`, `SameSite=Lax`, and `Secure` in production.
* Ensure all state-changing cookie-authenticated routes stay same-origin in deployed ingress policies. If supporting cross-origin mutations, proper CSRF tokens must be added.

### AI Gateway and Key Security
* All Bring-Your-Own-Key (BYOK) configurations are encrypted in the local database using the `ENCRYPTION_KEY` via Fernet encryption and are never sent raw back to the settings page.
* When using Cloud AI features, usage logs record only coarse provider information, timestamps, and request statuses. Under no circumstances are prompts, diffs, repository code, raw secrets, or generated answers stored in persistent database logs.
* Configure `CLOUD_AI_PREVIEW_DAILY_LIMIT` conservatively to prevent API quota exhaustion, and disable Cloud modes by deleting respective provider environment secrets if required.

### Release & Verification Checklist
Before deploying any release, run the verification suite:
```powershell
# 1. Run full test suite
.venv\Scripts\python.exe -m pytest -q

# 2. Pre-compile python assets to verify syntactical correctness
.venv\Scripts\python.exe -m compileall app tests

# 3. Check database migrations state
.venv\Scripts\python.exe -m alembic heads
```

Always perform database migrations via `alembic upgrade head` in an isolated window before enabling services. If rollback is necessary, disable features first via Environment variables, then carefully downgrade the additive schema migrations.
