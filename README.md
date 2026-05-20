# Git Analytics

FastAPI bootstrap for the Git Analytics MVP.

## Phase 1 Scope

This phase only creates the project foundation:

- FastAPI application factory
- Standard JSON response envelope
- Trace ID middleware
- Structured JSON logging
- Centralized exception handling
- SQLAlchemy 2.0 session setup
- Alembic migration skeleton
- Health check endpoint

OAuth, GitHub sync, database models, analytics APIs, and dashboard pages are intentionally deferred.

## Requirements

- Python 3.11+
- SQLite for local development
- PostgreSQL-ready via `DATABASE_URL`

For production deployments, install a PostgreSQL driver variant supported by the target platform. This bootstrap uses `psycopg`; `psycopg[binary]` can be used when binary wheels are available for the runtime.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

Open:

- App: http://localhost:8000
- Health check: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs

## Test

```bash
pytest
```

## Alembic

Create a migration after models are added:

```bash
alembic revision --autogenerate -m "create initial tables"
alembic upgrade head
```
