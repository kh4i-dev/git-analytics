# Developer Intelligence Platform (Git Analytics)

Git Analytics is a premium, self-hosted **Developer Intelligence Platform** built using FastAPI, SQLAlchemy 2.0, Jinja2, and Vanilla CSS. It connects to the GitHub API via secure OAuth, synchronizes repository data, and serves as a developer dashboard featuring detailed metrics, contribution heatmaps, streaks, convention breakdowns, and a live developer ecosystem explore feed.

---

## ⚡ Features

### 🔐 Security & Authentication
- **Secure GitHub OAuth**: Seamless login/logout using GitHub App scopes (`repo` + `read:user`), allowing access to both public and private repositories.
- **Fernet Token Encryption**: GitHub access tokens are symmetrically encrypted in the database (`users.encrypted_github_token`) and decrypted strictly in memory when calling external APIs.
- **Signed Session Cookies**: Cryptographically signed `httpOnly`, `secure`, and `sameSite` cookie sessions protect user interactions.

### 🔄 Repository Data Synchronization
- **Pre-sync Rate Limit Guard**: Checks your active GitHub API quota before triggering any sync to prevent failures.
- **Incremental Sync Engine**: First sync pulls the repository's full historical data. Subsequent syncs leverage the GitHub API `since` parameter, pulling only data created/updated after `last_synced_at`.
- **Fault-Tolerant & Idempotent Upserts**: Handles interruptions gracefully. Sync errors are logged per-repository without destroying previously synced historical data.

### 📊 Developer Analytics Dashboard
- **Overview Module**: High-level telemetry summaries (commits, issues, PR counts) and dynamic timeline charts.
- **Commit Insights**: Interactive charts showing commit frequency, weekday radar, hourly productivity distribution, and conventional commit keyword tags (`feat`, `fix`, `refactor`, `docs`, `chore`).
- **Developer Streaks & Scores**: Tracks active coding streak counts, current streaks, longest streaks, and repo health activity scores (0-100 gauge scale).
- **Contribution Heatmap**: A CSS/SVG-based interactive contribution grid plotting commit count distribution across the last 365 days.
- **PR & Issue Intelligence**: Detailed metrics on average pull request resolution age, closure rate metrics, issue lifecycle time analytics, and bug/feature tag distributions.

### 🔭 Ecosystem Explore Feed
- **Cached Trending Repositories**: Parallel background fetchers loading trending GitHub repos with language filtering capabilities.
- **Hacker News & AI Dev Tools**: Fully aggregated live Hacker News stories and curated developer tools.
- **In-Memory TTL Caching**: Custom asyncio-based TTL cache layer preventing API rate limits (15-min cache for trending repos; 10-min cache for HN stories).

---

## 🛠️ Architecture & Tech Stack

- **Framework**: FastAPI (asynchronous ASGI app factory with Swagger UI).
- **ORM / Database**: SQLAlchemy 2.0 (async connection models) + Alembic migrations. Default is SQLite (`git_analytics.db`) for local, ready for PostgreSQL in production.
- **View Engine**: Jinja2 + Chart.js CDN for robust dynamic client rendering.
- **Styling**: Highly responsive custom Vanilla CSS (Vercel/Linear dark theme variables).
- **Testing**: pytest (complete integration and service contract testing).

---

## 🚀 Setup & Installation

### 1. Clone & Set Environment
Clone the repository and copy the env configuration file:
```bash
copy .env.example .env
```
Fill in the following fields in `.env`:
- `GITHUB_CLIENT_ID` (Your GitHub OAuth App client ID)
- `GITHUB_CLIENT_SECRET` (Your GitHub OAuth App client secret)
- `SECRET_KEY` (Used for session signing)
- `ENCRYPTION_KEY` (Used for encrypting tokens; must be a 32-byte url-safe base64 string)
- `DATABASE_URL` (SQLite file path e.g., `sqlite:///./git_analytics.db`)

### 2. Configure Virtual Môi trường
Create a virtual environment and install dependencies:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run Database Migrations
Synchronize your local database schemas to the current migration head:
```bash
alembic upgrade head
```

---

## 🏃 Running the Application

Start the local development server:
```bash
uvicorn app.main:app --reload
```
Open your browser and navigate to:
- **Application**: `http://localhost:8000`
- **Interactive Swagger API Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

---

## 🧪 Testing

Execute the complete, asynchronous mock test suite:
```bash
.venv\Scripts\python.exe -m pytest -q
```
Verify complete source compilation:
```bash
python -m compileall app tests
```
