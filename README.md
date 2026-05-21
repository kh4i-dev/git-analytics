# Git Analytics

Engineering Intelligence Platform for repository analytics, contributor insights, branch intelligence, and AI-powered engineering reports.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/fastapi-latest-009688)](https://fastapi.tiangolo.com)

---

## Product Positioning

Git Analytics is an Engineering Intelligence Workspace focused on:

- repository health scoring
- contributor insights and KPI tracking
- branch-aware analytics
- engineering KPIs and trends
- immutable engineering reports with public sharing
- AI-powered developer tooling (commit generation, PR review, repo Q&A)

Built as a self-hosted platform connecting to GitHub via secure OAuth. Designed for individual developers who want to understand their repository activity beyond what GitHub Insights provides.

---

## Screenshots

_Add screenshots here for maximum impact._

| Dashboard Overview | Contribution Heatmap |
|---|---|
| `![dashboard](screenshots/dashboard.png)` | `![heatmap](screenshots/heatmap.png)` |

| Repository Analytics | AI Workspace |
|---|---|
| `![analytics](screenshots/analytics.png)` | `![ai-tools](screenshots/ai-tools.png)` |

| Report Export | Branch Analytics |
|---|---|
| `![export](screenshots/export.png)` | `![branch](screenshots/branch.png)` |

---

## Features

- Multi-branch analytics with branch selector
- Contributor KPI tracking and profiles
- Engineering health scoring (0-100 gauge)
- GitHub OAuth integration with encrypted token storage
- AI commit message generator and PR diff reviewer
- AI repository assistant for natural language Q&A
- Export PDF and Excel engineering reports
- Immutable engineering snapshots with capability URL sharing
- Public report revoke and token rotation
- Report anonymization for public viewers
- GitHub / Vercel-inspired dark SaaS UI
- Contribution heatmap (365-day GitHub-style grid)
- Activity insights (streaks, time-of-day, weekday distribution)
- Pre-sync rate limit guard
- Incremental sync engine (full first, then since)

---

## Architecture

```mermaid
graph TB
    Client["Browser (Jinja2 + Chart.js)"]
    
    subgraph FastAPI["FastAPI Application"]
        Routes["Routes Layer<br/>/dashboard/* /api/v1/* /auth/* /reports/*"]
        Services["Service Layer<br/>Sync | Analytics | Reports | AI | Export"]
        Clients["Client Layer<br/>GitHub REST API (paginated, rate-limited)"]
        DB["Data Layer<br/>SQLAlchemy 2.0 + Alembic"]
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

### System Workflows

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
| **Frontend** | Jinja2 + Chart.js | Server-rendered pages, interactive charts, dark SaaS UI |
| **Routes** | FastAPI | HTTP handling, hybrid page/API routing |
| **Services** | Python | Business logic orchestration, domain exceptions |
| **Clients** | httpx | GitHub REST API, pagination, rate limit handling |
| **ORM** | SQLAlchemy 2.0 | Data access, upsert, migration (Alembic) |
| **Database** | SQLite / PostgreSQL | Persistence

---

## Current Scope

### Phase 1 (Active)
- Single repository intelligence
- Immutable engineering reports with public sharing (capability URL)
- Manual sync architecture (button press, no background worker)
- AI workspace with local fallback mode
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
- Contributor identity resolution (aliases, email mapping, confidence scoring)
- Cross-repo analytics and ranking

---

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

---

## Not in Scope (Phase 1)

- Background sync worker — sync is manual
- Cross-repo aggregation — single-repo only
- Contributor identity resolution — simple mapping only
- Scheduled report generation — manual generation only
- Multi-user workspace — single-user deployment
- Password-protected reports — capability URL only
- Expiring public links — non-expiring by default
- Enterprise RBAC — no role system
- High-stakes cross-repo KPI — not accurate with current identity mapping

---

## Quick Start

### 1. Clone repository

```bash
git clone https://github.com/kh4i-dev/git-analytics.git
cd git-analytics
```

### 2. Setup environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure GitHub OAuth

Register an OAuth App at GitHub Settings > Developer Settings > OAuth Apps.

Copy the configuration file:

```bash
copy .env.example .env
```

### 4. Configure environment variables

| Variable | Required | Description |
|---|---|---|
| `GITHUB_CLIENT_ID` | Yes | Your GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | Yes | Your GitHub OAuth App client secret |
| `SECRET_KEY` | Yes | Session signing key (generate with `os.urandom(24)`) |
| `ENCRYPTION_KEY` | Yes | 32-byte url-safe base64 Fernet key |
| `DATABASE_URL` | No | Default: `sqlite:///./git_analytics.db`. Use PostgreSQL for production |

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Start server

```bash
uvicorn app.main:app --reload
```

- Application: `http://localhost:8000`
- API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

---

## Testing

```bash
.venv\Scripts\python.exe -m pytest -q
python -m compileall app tests
```

---

## Known Limitations

- Sync is manual (button press) — no background worker yet
- Contributor identity resolution is simple (github_login with email fallback); the same person using multiple emails may appear as separate contributors
- Multi-repo intelligence is planned for a later phase
- Reports are single-repository scoped in Phase 1
- Public reports do not support password protection or expiring links in Phase 1
- Token encryption uses Fernet (symmetric); key rotation requires re-encryption

---

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
