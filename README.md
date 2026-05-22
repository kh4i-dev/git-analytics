# Git Analytics

Engineering Intelligence Platform for GitHub repository analytics, contributor insights, branch intelligence, and engineering reports.

<p>
  <a href="https://github.com/kh4i-dev/git-analytics/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python"></a>
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/fastapi-latest-009688" alt="FastAPI"></a>
</p>

**Topics**: `fastapi` `github-api` `analytics` `developer-tools` `engineering-dashboard` `sqlalchemy` `chartjs` `python`

---

Self-hosted platform connecting to GitHub via secure OAuth. Syncs repository data and provides engineering-grade analytics, AI-powered insights, and immutable shareable reports.

## Features

- Repository health scoring and KPI tracking
- Branch-aware analytics with branch selector
- Contributor profiles with activity breakdown
- Engineering reports (immutable snapshots with public sharing)
- Report revoke, token rotation, and anonymization
- PDF and Excel export
- AI commit message generator and PR diff reviewer
- AI repository assistant (natural language Q&A)
- Contribution heatmap (365-day GitHub-style grid)
- Activity insights (streaks, time-of-day, weekday)
- Pre-sync rate limit guard
- Incremental sync engine
- GitHub OAuth with encrypted token storage
- Dark SaaS UI (GitHub/Vercel-inspired)

## Architecture

```mermaid
graph TB
    Client["Browser (Jinja2 + Chart.js)"]

    subgraph FastAPI["FastAPI Application"]
        Routes["Routes Layer<br>/dashboard/* /api/v1/* /auth/* /reports/*"]
        Services["Service Layer<br>Sync | Analytics | Reports | AI | Export"]
        Clients["Client Layer<br>GitHub REST API (paginated, rate-limited)"]
        DB["Data Layer<br>SQLAlchemy 2.0 + Alembic"]
    end

    GitHub["GitHub REST API"]
    Database["SQLite (dev) / PostgreSQL (prod)"]

    Client -- page routes --> Routes
    Client -- API routes --> Routes
    Routes --> Services
    Services --> Clients
    Services --> DB
    Clients --> GitHub
    DB --> Database
```

```mermaid
sequenceDiagram
    participant U as User
    participant B as Browser
    participant R as Routes
    participant S as Services
    participant C as Clients
    participant G as GitHub API
    participant D as Database

    Note over U,D: OAuth Login
    U->>B: Click Login
    B->>R: GET /auth/github/login
    R->>G: Redirect to GitHub OAuth
    G->>B: Authorization prompt
    U->>G: Approve
    G->>R: Callback with code
    R->>G: Exchange code for token
    G->>R: access_token
    R->>D: Encrypt and store token
    R->>B: Set signed cookie, redirect

    Note over U,D: Data Sync
    U->>B: Click Sync
    B->>R: POST /api/v1/sync
    R->>S: SyncService.sync()
    S->>C: Check rate limit
    C->>G: GET /rate_limit
    G->>C: remaining: 4500
    C->>G: GET /commits?per_page=100
    G->>C: Page 1 (100 commits)
    C->>G: GET /commits?page=2
    G->>C: Page 2 ...
    C->>G: GET /pulls?state=all
    G->>C: Pull requests
    C->>G: GET /issues?state=all
    G->>C: Issues
    S->>D: Upsert all data
    S->>D: Update last_synced_at
    R->>B: Sync complete

    Note over U,D: Analytics Dashboard
    U->>B: Open Dashboard
    B->>R: GET /dashboard/overview
    R->>B: HTML skeleton
    B->>R: fetch /api/v1/analytics
    R->>S: AnalyticsService.get_metrics()
    S->>D: SQL aggregation queries
    D->>S: Aggregated results
    R->>B: JSON response
    B->>B: Chart.js render

    Note over U,D: Report Generation
    U->>B: Generate Report
    B->>R: POST /api/v1/reports
    R->>S: EngineeringReportService
    S->>S: Snapshot analytics state
    S->>S: Generate release notes
    S->>S: Compute risk insights
    S->>D: Serialize snapshot
    R->>B: Report ready
    B->>B: Show capability URL
```

### Layered Stack

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | Jinja2 + Chart.js | Server-rendered pages, interactive charts, dark SaaS UI |
| Routes | FastAPI | HTTP handling, hybrid page and API routing |
| Services | Python | Business logic orchestration, domain exceptions |
| Clients | httpx | GitHub REST API, pagination, rate limit handling |
| ORM | SQLAlchemy 2.0 | Data access, upsert, schema migrations |
| Database | SQLite / PostgreSQL | Persistence |

### Sync State Machine

```mermaid
stateDiagram-v2
    direction LR
    [*] --> pending: Repository connected
    pending --> syncing: User clicks Sync

    state syncing {
        [*] --> checking_rate_limit
        checking_rate_limit --> fetching_commits: Quota sufficient
        checking_rate_limit --> sync_error: Quota exceeded
        fetching_commits --> fetching_pull_requests
        fetching_pull_requests --> fetching_issues
        fetching_issues --> persisting_data
        persisting_data --> [*]
    }

    syncing --> success: All data persisted
    syncing --> sync_error: Error at any step
    success --> syncing: Incremental sync
    sync_error --> syncing: Retry
    success --> [*]
    sync_error --> [*]
```

## Current Scope

### Phase 1 (Active)
- Single repository intelligence
- Immutable engineering reports with public sharing (capability URL)
- User-triggered and single-process queued sync
- AI workspace with encrypted BYOK and Cloud AI preview modes
- PDF and Excel export
- GitHub OAuth authentication

### Phase 2 (Planned)
- Hosted AI providers (OpenAI, Gemini, BYOK)
- Scheduled report generation groundwork
- AI insight layer across all analytics

### Phase 3 (Planned)
- Background workers and queue system
- Async sync engine with retry and recovery
- Tenant isolation

### Phase 4 (Planned)
- Multi-repo intelligence
- Contributor identity resolution
- Cross-repo analytics and ranking

## Not in Scope (Phase 1)

- External/multi-process sync worker deployment
- Cross-repo aggregation
- Contributor identity resolution
- Scheduled report generation
- Multi-user workspace
- Password-protected reports
- Expiring public links
- Enterprise RBAC
- High-stakes cross-repo KPI

## Quick Start

### Prerequisites

- Python 3.11+
- GitHub OAuth App (GitHub Settings > Developer Settings > OAuth Apps)

### 1. Clone

```bash
git clone https://github.com/kh4i-dev/git-analytics.git
cd git-analytics
```

### 2. Configure

```bash
copy .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `GITHUB_CLIENT_ID` | Yes | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | Yes | GitHub OAuth App client secret |
| `SECRET_KEY` | Yes | Session signing key (`os.urandom(24)`). |
| `ENCRYPTION_KEY` | Yes | 32-byte url-safe base64 Fernet key |
| `DATABASE_URL` | No | Default: `sqlite:///./git_analytics.db` |

### 3. Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Migrate

```bash
alembic upgrade head
```

### 5. Run

```bash
uvicorn app.main:app --reload
```

| URL | Description |
|---|---|
| `http://localhost:8000` | Application |
| `http://localhost:8000/docs` | API documentation |
| `http://localhost:8000/health` | Health check |

## Testing

```bash
.venv\Scripts\python.exe -m pytest -q
python -m compileall app tests
```

## Known Limitations

- Sync queue is single-process; hosted deployments still need an external worker strategy
- Contributor identity resolution is simple (github_login with email fallback); same person using multiple emails may appear as separate contributors
- Reports are single-repository scoped in Phase 1
- Public reports do not support password protection or expiring links
- Token encryption uses Fernet (symmetric); key rotation requires re-encryption

## Documentation

| File | Description |
|---|---|
| [CONTEXT.md](CONTEXT.md) | Domain glossary and product principles |
| [docs/architecture.md](docs/architecture.md) | System architecture and data flows |
| [docs/walkthrough.md](docs/walkthrough.md) | End-to-end user flow |
| [docs/roadmap.md](docs/roadmap.md) | Phase roadmap with scope boundaries |
| [docs/report-system.md](docs/report-system.md) | Engineering report system |
| [docs/ai-tools.md](docs/ai-tools.md) | AI workspace documentation |
| [docs/ui-guidelines.md](docs/ui-guidelines.md) | Design system and UI patterns |
| [docs/changelog.md](docs/changelog.md) | Full release history |
