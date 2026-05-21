# Git Analytics — Engineering Intelligence Platform

Git Analytics is an Engineering Intelligence Platform — a self-hosted Dev Analytics SaaS and Repository Intelligence Workspace. Built with FastAPI, SQLAlchemy 2.0, Jinja2, and Vanilla CSS, it connects to GitHub via secure OAuth, synchronizes repository data, and delivers engineering-grade analytics, AI-powered insights, immutable reports, and public sharing via capability URL.

---

## Features

### Security & Authentication
- **Secure GitHub OAuth**: Login/logout using GitHub App scopes (`repo` + `read:user`), granting access to public and private repositories.
- **Fernet Token Encryption**: GitHub access tokens are symmetrically encrypted in the database and decrypted strictly in memory.
- **Signed Session Cookies**: `httpOnly`, `secure`, and `sameSite` cookie sessions.

### Repository Data Synchronization
- **Pre-sync Rate Limit Guard**: Checks GitHub API quota before syncing.
- **Incremental Sync Engine**: Full first sync, subsequent syncs fetch only new data via `since` parameter.
- **Multi-Branch Sync**: Sync all branches or select individual branches.
- **Fault-Tolerant Upserts**: Interruptions do not destroy previously synced data.
- **Sync States**: pending, syncing, success, failed — with color-coded badges.

### Engineering Analytics
- **Repository Analytics**: Full per-repo breakdown of commits, PRs, issues.
- **Branch Analytics**: Per-branch analytics with branch selector.
- **Contributor Analytics**: Per-contributor profiles with activity breakdown.
- **Executive Overview**: Health score, velocity, contributor trends.
- **Commit Heatmap**: 365-day GitHub-style contribution grid (CSS grid, responsive).
- **KPI Scoring**: Activity score with health gauge (0-100).
- **PR Intelligence**: Merge time, closure rate, status distribution.
- **Issue Intelligence**: Open/closed rate, label analytics, time to close.
- **Activity Insights**: Streaks, time-of-day, weekday distribution.

### Engineering Reports
- **Immutable Snapshots**: Point-in-time capture of repository analytics.
- **Release Notes**: Auto-generated from commit and PR data.
- **Changelog**: Structured changelog generation.
- **Risk Insights**: Automated risk analysis based on repository activity.
- **Public Sharing**: Capability URL access with revoke and token rotation.
- **Report Anonymization**: Hide repository name in public view.
- **PDF and Excel Export**: Download reports as PDF or spreadsheet.

### AI Workspace
- **Commit Message Generator**: Generate conventional commits from staged changes.
- **PR Diff Reviewer**: AI-powered code review and suggestions.
- **Repo Assistant**: Natural language Q&A over repository data.
- **Local Fallback Mode**: Runs on-device, no API key required.
- **Future Hosted Providers**: OpenAI, Gemini, BYOK architecture ready.

### Ecosystem Explore Feed
- **Cached Trending Repositories**: Parallel background fetchers loading trending GitHub repos with language filtering.
- **Hacker News and AI Dev Tools**: Aggregated Hacker News stories and curated developer tools.
- **In-Memory TTL Caching**: Custom asyncio-based cache layer preventing API rate limits.

---

## Architecture and Tech Stack

- **Framework**: FastAPI (async ASGI app factory with Swagger UI)
- **ORM / Database**: SQLAlchemy 2.0 + Alembic migrations. SQLite (dev), PostgreSQL (prod)
- **View Engine**: Jinja2 + Chart.js for dynamic client rendering
- **Styling**: Custom Vanilla CSS (dark theme)
- **Testing**: pytest (integration and service contract testing)
- **AI**: Local fallback mode (Phase 1), hosted providers ready (Phase 2)

### Layered Architecture

```
Routes -> Services -> Repositories / Clients -> Database / GitHub API
```

Each layer has a single responsibility: routes handle HTTP, services orchestrate business logic, repositories persist data, clients communicate with external APIs.

See full architecture details in [docs/architecture.md](docs/architecture.md).

---

## Setup and Installation

### Prerequisites

- Python 3.11+
- GitHub OAuth App (register at GitHub Settings > Developer Settings > OAuth Apps)

### 1. Clone and Configure

```bash
git clone <repo-url>
cd git-analytics
copy .env.example .env
```

Fill in the following fields in `.env`:

| Variable | Description |
|---|---|
| `GITHUB_CLIENT_ID` | Your GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | Your GitHub OAuth App client secret |
| `SECRET_KEY` | Used for session signing |
| `ENCRYPTION_KEY` | 32-byte url-safe base64 string for token encryption |
| `DATABASE_URL` | SQLite path (e.g. `sqlite:///./git_analytics.db`) or PostgreSQL URL |

### 2. Install Dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run Database Migrations

```bash
alembic upgrade head
```

---

## Running the Application

```bash
uvicorn app.main:app --reload
```

- Application: `http://localhost:8000`
- API Documentation (Swagger): `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

---

## Testing

```bash
.venv\Scripts\python.exe -m pytest -q
python -m compileall app tests
```

---

## Documentation

| File | Description |
|---|---|
| [CONTEXT.md](CONTEXT.md) | Domain glossary, architecture decisions, product principles |
| [docs/architecture.md](docs/architecture.md) | System architecture, data flows, error handling |
| [docs/walkthrough.md](docs/walkthrough.md) | End-to-end user flow walkthrough |
| [docs/roadmap.md](docs/roadmap.md) | Phase roadmap (1-4) with scope boundaries |
| [docs/changelog.md](docs/changelog.md) | Full release history |
| [docs/release-notes.md](docs/release-notes.md) | Versioned release notes |
| [docs/report-system.md](docs/report-system.md) | Engineering report system details |
| [docs/ai-tools.md](docs/ai-tools.md) | AI workspace documentation |
| [docs/ui-guidelines.md](docs/ui-guidelines.md) | Design system and UI patterns |
| [docs/phase1-product-discovery.md](docs/phase1-product-discovery.md) | Product discovery |
| [docs/phase2-system-design.md](docs/phase2-system-design.md) | System design |
| [docs/phase3-database-design.md](docs/phase3-database-design.md) | Database schema design |
| [docs/phase4-api-design.md](docs/phase4-api-design.md) | API design specifications |
| [docs/phase5-uml-and-report.md](docs/phase5-uml-and-report.md) | UML diagrams and report mapping |

---

## Project Status

Strong Phase 1 foundation established: engineering analytics, AI workspace (local fallback), immutable reports with public sharing, SaaS-grade UI. Roadmap extends through Phase 4 (multi-repo intelligence). See [docs/roadmap.md](docs/roadmap.md) for details.
