# Phase 2 — System Design

## 2.1 Architecture Overview

### Kiến trúc tổng thể

Hệ thống Git Analytics sử dụng kiến trúc **Layered Architecture (3-layer)** kết hợp với **Hybrid Routing** (server-rendered pages + JSON API).

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                          │
├─────────────────────────────────────────────────────────────────┤
│  Jinja2 HTML Pages          │  JavaScript (fetch → Chart.js)    │
│  - Layout, Sidebar, Forms   │  - Gọi /api/v1/* endpoints       │
│  - Server-rendered           │  - Render biểu đồ async          │
└──────────────┬───────────────┴──────────────┬───────────────────┘
               │ HTTP (page routes)            │ HTTP (API routes)
               ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI APPLICATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    ROUTES LAYER                           │    │
│  │  Page Routes: /dashboard/*, /repositories/*              │    │
│  │  API Routes:  /api/v1/analytics/*, /api/v1/sync/*        │    │
│  │  Auth Routes: /auth/login, /auth/github/callback, /auth/logout  │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                              │                                    │
│  ┌──────────────────────────▼──────────────────────────────┐    │
│  │                   SERVICE LAYER                           │    │
│  │  AuthService │ SyncService │ AnalyticsService             │    │
│  │  - Business logic                                         │    │
│  │  - Orchestration                                          │    │
│  │  - Domain exceptions                                      │    │
│  └───────┬──────────────────┬──────────────────────────────┘    │
│           │                  │                                    │
│  ┌────────▼────────┐  ┌─────▼─────────────────────────────┐    │
│  │  CLIENTS LAYER  │  │        REPOSITORY LAYER            │    │
│  │  GitHubClient   │  │  UserRepo │ CommitRepo │ PRRepo    │    │
│  │  - HTTP calls   │  │  IssueRepo │ RepositoryRepo        │    │
│  │  - Pagination   │  │  - CRUD + Upsert                   │    │
│  │  - Rate limit   │  │  - SQL aggregation                  │    │
│  └────────┬────────┘  └─────────────────┬──────────────────┘    │
│           │                              │                        │
└───────────┼──────────────────────────────┼────────────────────────┘
            │                              │
            ▼                              ▼
┌───────────────────┐          ┌───────────────────────┐
│   GitHub REST API  │          │      DATABASE          │
│   api.github.com   │          │  SQLite (dev)          │
│                    │          │  PostgreSQL (prod)     │
└───────────────────┘          └───────────────────────┘
```

### Nguyên tắc thiết kế

| Nguyên tắc | Áp dụng |
|---|---|
| Separation of Concerns | Mỗi layer chỉ làm 1 việc: route nhận request, service xử lý logic, repository thao tác DB |
| Dependency Injection | Service nhận GitHubClient và Repository qua constructor/parameter |
| Single Responsibility | Mỗi service/class có 1 trách nhiệm rõ ràng |
| Open/Closed | Thêm analytics metric mới không cần sửa AnalyticsService interface |
| Interface Segregation | GitHubClient chỉ expose methods mà SyncService cần |
| Stateless API | Mỗi API request tự chứa đủ context (cookie → user_id → token) |

---

## 2.2 Tại sao chọn FastAPI

| Tiêu chí | FastAPI | Flask | Django |
|---|---|---|---|
| Async support | ✅ Native | ❌ (extension) | ⚠️ (3.1+) |
| Auto API docs (Swagger) | ✅ Built-in | ❌ | ❌ |
| Type hints + validation | ✅ Pydantic | ❌ | ❌ |
| Performance | Cao (Starlette) | Trung bình | Trung bình |
| Learning curve | Thấp | Thấp | Cao |
| Template support | ✅ Jinja2 | ✅ Jinja2 | Django Templates |
| ORM flexibility | Bất kỳ (SQLAlchemy) | Bất kỳ | Django ORM (locked) |
| Phù hợp API-first | ✅ Sinh ra cho API | ⚠️ Có thể | ⚠️ REST framework |

**Lý do chọn FastAPI:**
1. **Swagger UI tự động** — demo API trực tiếp trên browser, không cần Postman
2. **Pydantic validation** — request/response schema rõ ràng, tự generate docs
3. **Async HTTP client** — gọi GitHub API hiệu quả với `httpx` async
4. **Nhẹ và linh hoạt** — không bị lock vào ORM hay template engine cụ thể
5. **Phổ biến trong industry** — kỹ năng có giá trị cho portfolio

---

## 2.3 Module / Service Boundaries

### Sơ đồ module

```
┌─────────────────────────────────────────────────────────┐
│                     APP MODULES                          │
├─────────────┬──────────────┬──────────────┬─────────────┤
│    AUTH      │     SYNC     │  ANALYTICS   │    CORE     │
├─────────────┼──────────────┼──────────────┼─────────────┤
│ OAuth flow  │ GitHubClient │ CommitStats  │ Config      │
│ Session mgmt│ SyncService  │ PRStats      │ Exceptions  │
│ Token encrypt│ Rate limit  │ IssueStats   │ Logging     │
│ Login/Logout│ Pagination   │ OverviewStats│ Security    │
│             │ Error handle │              │ DB Session  │
└─────────────┴──────────────┴──────────────┴─────────────┘
```

### Trách nhiệm từng module

**AUTH Module**
- Xử lý GitHub OAuth flow (redirect → callback → token exchange)
- Mã hóa/giải mã GitHub access token
- Quản lý signed cookie session
- Middleware xác thực user cho protected routes

**SYNC Module**
- GitHubClient: giao tiếp GitHub REST API
- SyncService: điều phối luồng sync (full/incremental)
- Rate limit checking trước và trong sync
- Upsert data vào database qua repository layer

**ANALYTICS Module**
- AnalyticsService: chạy SQL aggregation queries
- Trả về dữ liệu đã tính toán cho API routes
- Không biết về HTTP hay chart rendering

**CORE Module**
- Config: đọc .env, quản lý settings
- Exceptions: domain exception hierarchy
- Logging: structured logging với trace_id
- Security: encryption utilities
- DB Session: SQLAlchemy session factory

### Dependency Rules

```
Routes → Services → Repositories → Models
                  → Clients (GitHubClient)

Rules:
- Routes KHÔNG gọi Repositories trực tiếp
- Routes KHÔNG gọi GitHubClient trực tiếp
- Services KHÔNG import FastAPI (Request, Response, HTTPException)
- GitHubClient KHÔNG import SQLAlchemy
- Models KHÔNG import bất kỳ layer nào khác
```

---

## 2.4 Folder Structure

```
git-analytics/
├── app/
│   ├── main.py                          # FastAPI app factory, middleware, exception handlers
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                    # Settings from .env (Pydantic BaseSettings)
│   │   ├── security.py                  # Token encryption/decryption, cookie signing
│   │   ├── exceptions.py               # Domain exception hierarchy
│   │   ├── exception_handlers.py       # Map domain exceptions → HTTP responses
│   │   └── logging.py                  # Structured logging setup, trace_id
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py                   # SQLAlchemy engine + session factory
│   │   └── base.py                      # DeclarativeBase for models
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                      # User table (github_id, encrypted_token, etc.)
│   │   ├── repository.py               # Repository table (sync status fields)
│   │   ├── contributor.py              # Contributor table (login/email identity)
│   │   ├── commit.py                    # Commit table
│   │   ├── pull_request.py             # PullRequest table
│   │   └── issue.py                     # Issue table (labels as JSON)
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── user_repo.py
│   │   ├── repository_repo.py
│   │   ├── contributor_repo.py
│   │   ├── commit_repo.py
│   │   ├── pull_request_repo.py
│   │   └── issue_repo.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py             # OAuth flow, token management
│   │   ├── sync_service.py             # Sync orchestration
│   │   └── analytics_service.py        # Dashboard data computation
│   ├── clients/
│   │   ├── __init__.py
│   │   └── github_client.py            # GitHub REST API adapter
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py                      # /auth/login, /auth/github/callback, /auth/logout
│   │   ├── pages.py                     # /dashboard/*, /repositories/* (Jinja2)
│   │   ├── api_repositories.py         # /api/v1/repositories/*
│   │   ├── api_sync.py                  # /api/v1/sync/*
│   │   └── api_analytics.py            # /api/v1/analytics/*
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── response.py                 # StandardResponse, ErrorResponse
│   │   ├── repository.py               # RepositoryOut, RepositoryList
│   │   └── analytics.py                # CommitStats, PRStats, IssueStats
│   ├── templates/
│   │   ├── base.html                    # Layout: sidebar, navbar, footer
│   │   ├── auth/
│   │   │   └── login.html
│   │   ├── dashboard/
│   │   │   ├── overview.html
│   │   │   ├── commits.html
│   │   │   ├── pulls.html
│   │   │   └── issues.html
│   │   └── repositories/
│   │       ├── list.html
│   │       └── detail.html
│   └── static/
│       ├── css/
│       └── js/
│           ├── chart-loader.js          # Generic chart loading via API
│           └── sync.js                  # Sync button handler
├── migrations/                           # Alembic migrations
│   ├── versions/
│   └── env.py
├── tests/
│   ├── unit/
│   │   ├── test_sync_service.py
│   │   ├── test_analytics_service.py
│   │   └── test_github_client.py
│   └── integration/
│       └── test_api_endpoints.py
├── .env.example                          # Template for secrets
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md
```

---

## 2.5 Data Flow — Luồng chính

### Flow 1: Login GitHub OAuth

```
User                Browser              FastAPI              GitHub
 │                    │                    │                    │
 │──── Click Login ──▶│                    │                    │
 │                    │── GET /auth/login─▶│                    │
 │                    │                    │── Build OAuth URL──│
 │                    │◀─ Redirect 302 ────│                    │
 │                    │──────────────── Redirect ──────────────▶│
 │                    │                    │                    │
 │◀── GitHub Login ───│                    │                    │
 │── Approve scope ──▶│                    │                    │
 │                    │◀── Redirect + code ─────────────────────│
 │                    │── GET /auth/github/callback?code=xxx ───▶│
 │                    │                    │── POST /access_token│
 │                    │                    │◀── access_token ───│
 │                    │                    │── GET /user ────────│
 │                    │                    │◀── user profile ───│
 │                    │                    │                    │
 │                    │                    │── Encrypt token     │
 │                    │                    │── Upsert user to DB │
 │                    │                    │── Set signed cookie │
 │                    │◀─ Redirect /dashboard ─│               │
 │                    │                    │                    │
```

### Flow 2: Chọn Repository & Sync

```
User              Browser              FastAPI             GitHub API         Database
 │                  │                    │                    │                  │
 │── Open repos ───▶│                    │                    │                  │
 │                  │── GET /repositories─▶│                    │                  │
 │                  │                    │── Decrypt token     │                  │
 │                  │                    │── GET /user/repos──▶│                  │
 │                  │                    │◀── repos list ──────│                  │
 │                  │◀── HTML + repo list│                    │                  │
 │                  │                    │                    │                  │
 │── Connect repo ─▶│                    │                    │                  │
 │                  │── POST /api/v1/repositories ───────────▶│                  │
 │                  │                    │── Save repo ────────────────────────▶│
 │                  │◀── 201 Created ────│                    │                  │
 │                  │                    │                    │                  │
 │── Click Sync ───▶│                    │                    │                  │
 │                  │── POST /api/v1/repositories/{id}/sync ─▶│                  │
 │                  │                    │                    │                  │
 │                  │                    │── GET /rate_limit──▶│                  │
 │                  │                    │◀── remaining: 4500──│                  │
 │                  │                    │                    │                  │
 │                  │                    │── Check last_synced_at ──────────────▶│
 │                  │                    │◀── null (first sync) ────────────────│
 │                  │                    │                    │                  │
 │                  │                    │── GET /commits?per_page=100 ────────▶│
 │                  │                    │◀── page 1 (100 commits) ────────────│
 │                  │                    │── GET /commits?page=2 ──────────────▶│
 │                  │                    │◀── page 2 ... ─────────────────────│
 │                  │                    │                    │                  │
 │                  │                    │── GET /pulls?state=all&per_page=100─▶│
 │                  │                    │◀── PRs ────────────────────────────│
 │                  │                    │                    │                  │
 │                  │                    │── GET /issues?per_page=100 ─────────▶│
 │                  │                    │◀── issues ─────────────────────────│
 │                  │                    │                    │                  │
 │                  │                    │── Upsert commits ────────────────────▶│
 │                  │                    │── Upsert PRs ────────────────────────▶│
 │                  │                    │── Upsert issues ─────────────────────▶│
 │                  │                    │── Update last_synced_at ─────────────▶│
 │                  │                    │                    │                  │
 │                  │◀── 200 OK (sync complete) ──────────────│                  │
```

### Flow 3: Dashboard Analytics

```
User              Browser              FastAPI                    Database
 │                  │                    │                          │
 │── Open dashboard▶│                    │                          │
 │                  │── GET /dashboard/commits ──▶│                  │
 │                  │◀── HTML skeleton ──│                          │
 │                  │                    │                          │
 │                  │── fetch /api/v1/analytics/commits?repo_id=1──▶│
 │                  │                    │── SELECT date, COUNT(*)  │
 │                  │                    │   FROM commits           │
 │                  │                    │   WHERE repo_id=1        │
 │                  │                    │   GROUP BY date ─────────▶│
 │                  │                    │◀── aggregated rows ──────│
 │                  │◀── JSON { data: {...} } ──│                  │
 │                  │                    │                          │
 │                  │── Chart.js render ─│                          │
 │◀── Biểu đồ ─────│                    │                          │
```

---

## 2.6 GitHub API Integration Flow

### Endpoints sử dụng

| Mục đích | Endpoint | Method | Params |
|---|---|---|---|
| Rate limit check | `/rate_limit` | GET | — |
| User profile | `/user` | GET | — |
| User repos | `/user/repos` | GET | `type=owner&per_page=100` |
| Commits | `/repos/{owner}/{repo}/commits` | GET | `per_page=100&since=` |
| Pull Requests | `/repos/{owner}/{repo}/pulls` | GET | `state=all&per_page=100&since=` |
| Issues | `/repos/{owner}/{repo}/issues` | GET | `state=all&per_page=100&since=` |

### Pagination Strategy

GitHub API dùng **Link header** cho pagination:

```
Link: <https://api.github.com/...?page=2>; rel="next",
      <https://api.github.com/...?page=5>; rel="last"
```

GitHubClient pagination algorithm:
1. Gọi page 1 với `per_page=100`
2. Đọc `Link` header, tìm `rel="next"`
3. Nếu có next → gọi tiếp
4. Nếu không có next → hết data
5. Mỗi page, kiểm tra `X-RateLimit-Remaining` → nếu = 0 thì dừng, raise `GitHubRateLimitExceeded`

### Incremental Sync Logic

```
IF repository.last_synced_at IS NULL:
    # Full sync — không có since parameter
    commits = github_client.get_commits(owner, repo)
    pulls = github_client.get_pulls(owner, repo)
    issues = github_client.get_issues(owner, repo)
ELSE:
    # Incremental — chỉ lấy data mới
    since = repository.last_synced_at.isoformat()
    commits = github_client.get_commits(owner, repo, since=since)
    pulls = github_client.get_pulls(owner, repo, since=since)
    issues = github_client.get_issues(owner, repo, since=since)

# Upsert tất cả vào DB (tránh duplicate bằng unique constraint)
repository_repo.upsert_commits(commits)
repository_repo.upsert_pulls(pulls)
repository_repo.upsert_issues(issues)

# Cập nhật sync status
repository.last_synced_at = datetime.utcnow()
repository.last_sync_status = "success"
```

---

## 2.7 Authentication Flow

### OAuth Sequence

```
1. User clicks "Login with GitHub"
2. Server builds GitHub OAuth URL:
   https://github.com/login/oauth/authorize
     ?client_id=GITHUB_CLIENT_ID
     &redirect_uri=http://localhost:8000/auth/github/callback
     &scope=repo read:user
     &state=random_csrf_token
3. User approves on GitHub
4. GitHub redirects to /auth/github/callback?code=xxx&state=yyy
5. Server verifies state (CSRF protection)
6. Server exchanges code for access_token:
   POST https://github.com/login/oauth/access_token
   Body: { client_id, client_secret, code }
7. Server calls GET /user with token → gets github_id, login, name, avatar
8. Server upserts User record in DB
9. Server encrypts access_token → stores in users.encrypted_github_token
10. Server sets signed httpOnly cookie: { user_id: <id> }
11. Redirect to /dashboard
```

### Authentication Middleware

Mỗi protected route/API endpoint đi qua middleware:
1. Đọc signed cookie → extract `user_id`
2. Nếu không có cookie hoặc invalid → redirect /auth/login (pages) hoặc 401 (API)
3. Lookup user trong DB bằng `user_id`
4. Nếu user không tồn tại → clear cookie, redirect login
5. Attach `current_user` vào request state
6. Khi service cần token → decrypt `users.encrypted_github_token`

### Security Measures

| Measure | Implementation |
|---|---|
| CSRF protection | OAuth `state` parameter (random token, verify on callback) |
| Token encryption | Fernet symmetric encryption (from `cryptography` library) |
| Cookie security | `httpOnly=True`, `secure=True` (prod), `sameSite=lax` |
| Token in logs | NEVER — logging middleware redacts Authorization headers |
| Token in response | NEVER — API never returns raw token |
| Logout | Delete cookie + optionally clear encrypted_token in DB |

---

## 2.8 Sync Repository Workflow

### State Machine

```
                    ┌─────────────┐
                    │   PENDING   │  (repo vừa connect, chưa sync)
                    └──────┬──────┘
                           │ User clicks Sync
                           ▼
                    ┌─────────────┐
              ┌─────│  SYNCING    │─────┐
              │     └─────────────┘     │
              │                         │
         Rate limit              All pages
         exceeded /              fetched &
         API error               saved OK
              │                         │
              ▼                         ▼
     ┌─────────────┐          ┌─────────────┐
     │   FAILED    │          │   SUCCESS   │
     └──────┬──────┘          └──────┬──────┘
            │                         │
            │ User clicks Sync again  │ User clicks Sync again
            │ (retry from same point) │ (incremental)
            └─────────┐  ┌───────────┘
                      ▼  ▼
                ┌─────────────┐
                │  SYNCING    │
                └─────────────┘
```

### Sync Fields trên Repository

| Field | Type | Mô tả |
|---|---|---|
| `last_synced_at` | DateTime, nullable | Thời điểm sync thành công cuối cùng. NULL = chưa bao giờ sync |
| `last_sync_status` | String | "pending" / "syncing" / "success" / "failed" |
| `last_sync_error` | String, nullable | Mô tả lỗi nếu failed. NULL nếu success |
| `sync_started_at` | DateTime, nullable | Thời điểm bắt đầu sync hiện tại (detect stuck syncs) |

### Sync Process (Chi tiết)

```
1. PRE-CHECK
   ├── Verify user authenticated
   ├── Verify repository belongs to user
   ├── Check last_sync_status != "syncing" (prevent double sync)
   └── Call GET /rate_limit
       ├── If remaining < 50 → warn user, abort
       └── If remaining >= 50 → proceed

2. START SYNC
   ├── Set last_sync_status = "syncing"
   ├── Set sync_started_at = now()
   └── Clear last_sync_error = null

3. FETCH DATA
   ├── Determine mode: full (last_synced_at = null) or incremental
   ├── Fetch commits (paginated)
   │   └── On each page: check X-RateLimit-Remaining
   ├── Fetch pull requests (paginated)
   └── Fetch issues (paginated)

4. PERSIST DATA
   ├── Resolve contributors (login or email)
   ├── Upsert contributors
   ├── Upsert commits (unique: repo_id + sha)
   ├── Upsert pull requests (unique: repo_id + number)
   └── Upsert issues (unique: repo_id + number)

5. SUCCESS
   ├── Set last_synced_at = now()
   ├── Set last_sync_status = "success"
   └── Clear last_sync_error

6. ON ERROR (at any step)
   ├── Set last_sync_status = "failed"
   ├── Set last_sync_error = error message
   ├── Do NOT update last_synced_at
   └── Data already persisted in steps before error is kept
       (partial sync is safe because of upsert + incremental)
```

---

## 2.9 Error Handling Strategy

### Exception Hierarchy

```
AppException (base)
├── ValidationException          → 400 Bad Request
├── AuthenticationException      → 401 Unauthorized
├── AuthorizationException       → 403 Forbidden
├── RepositoryNotFoundException  → 404 Not Found
├── ConflictException            → 409 Conflict (e.g., sync already in progress)
├── GitHubAPIException (base)
│   ├── GitHubAuthFailed         → 401 (token revoked/expired)
│   ├── GitHubRateLimitExceeded  → 429 Too Many Requests
│   ├── GitHubNotFound           → 404 (repo deleted on GitHub)
│   └── GitHubServerError        → 502 Bad Gateway
├── SyncFailedException          → 500 Internal Server Error
└── DatabaseException            → 500 Internal Server Error
```

### Error Response Format (API)

```json
{
  "data": null,
  "error": {
    "code": "GITHUB_RATE_LIMIT_EXCEEDED",
    "message": "GitHub API rate limit exceeded. Resets at 2024-01-15T11:00:00Z.",
    "details": {
      "remaining": 0,
      "reset_at": "2024-01-15T11:00:00Z"
    }
  },
  "meta": {
    "trace_id": "abc123-def456",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Error Handling per Layer

| Layer | Responsibility | Ví dụ |
|---|---|---|
| **GitHubClient** | Map HTTP errors → domain exceptions | `403` → `GitHubRateLimitExceeded` |
| **Repository Layer** | Wrap DB errors → `DatabaseException` | `IntegrityError` → `ConflictException` |
| **Service Layer** | Raise business exceptions | Repo not found → `RepositoryNotFoundException` |
| **Routes** | Không catch — để exception handler xử lý | Pass-through |
| **Exception Handler** | Map domain exception → HTTP response | `GitHubRateLimitExceeded` → 429 JSON |

### Error Handling cho Pages vs API

| Loại route | Khi lỗi |
|---|---|
| Page routes (`/dashboard/*`) | Render error template với message thân thiện |
| API routes (`/api/v1/*`) | Return JSON error response |

---

## 2.10 Logging & Observability Strategy

### Structured Logging

Mỗi log entry có format JSON:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "trace_id": "abc123-def456",
  "user_id": 1,
  "module": "sync_service",
  "message": "Sync started",
  "context": {
    "repo_id": 5,
    "mode": "incremental",
    "since": "2024-01-10T00:00:00Z"
  }
}
```

### Trace ID

- Mỗi HTTP request được gán 1 `trace_id` (UUID) bởi middleware
- Trace ID truyền qua tất cả layers: route → service → repository → client
- Trace ID xuất hiện trong:
  - Log entries
  - Error responses (`meta.trace_id`)
  - GitHubClient request headers (optional, for debugging)
- Giúp trace toàn bộ luồng xử lý của 1 request khi debug

### Log Levels

| Level | Khi nào dùng | Ví dụ |
|---|---|---|
| **DEBUG** | Chi tiết kỹ thuật, chỉ bật khi dev | "Fetching commits page 3/7" |
| **INFO** | Sự kiện business quan trọng | "Sync completed: 150 commits, 12 PRs" |
| **WARNING** | Vấn đề tiềm ẩn nhưng không fail | "Rate limit remaining: 45 (low)" |
| **ERROR** | Operation failed | "Sync failed: GitHubRateLimitExceeded" |

### Không được log

- GitHub access token (dù encrypted hay raw)
- OAuth client_secret
- Encryption keys
- Full request/response bodies chứa sensitive data

### Monitoring Metrics (Production)

| Metric | Mô tả |
|---|---|
| `sync_duration_seconds` | Thời gian sync mỗi repository |
| `sync_success_total` | Số lần sync thành công |
| `sync_failure_total` | Số lần sync thất bại |
| `github_api_calls_total` | Tổng số request đến GitHub API |
| `github_rate_limit_remaining` | Quota còn lại sau mỗi sync |
| `dashboard_load_time_seconds` | Thời gian load analytics data |

*Lưu ý: MVP chỉ cần logging. Metrics monitoring triển khai khi production.*

---

## 2.11 Tech Stack Summary

| Component | Technology | Lý do |
|---|---|---|
| Language | Python 3.11+ | Yêu cầu đề tài |
| Web Framework | FastAPI | Async, auto-docs, type-safe |
| Template Engine | Jinja2 | Tích hợp sẵn FastAPI, đơn giản |
| ORM | SQLAlchemy 2.0 | Hỗ trợ async, type hints, mature |
| Migration | Alembic | Chuẩn cho SQLAlchemy |
| HTTP Client | httpx | Async, modern, requests-compatible API |
| Database (dev) | SQLite | Zero-config, file-based |
| Database (prod) | PostgreSQL | Robust, JSON support, production-ready |
| Charting | Chart.js | Nhẹ, đẹp, dễ dùng với vanilla JS |
| CSS Framework | Bootstrap 5 | Nhanh, responsive, component-rich |
| Token Encryption | cryptography (Fernet) | Standard library, symmetric encryption |
| Deployment | Railway / Render | Free tier, Git-based deploy |
| Testing | pytest + httpx | FastAPI test client |

---

## 2.12 Deployment Architecture

```
┌──────────────────────────────────────────────┐
│              Railway / Render                  │
├──────────────────────────────────────────────┤
│                                               │
│  ┌─────────────────┐    ┌─────────────────┐  │
│  │  FastAPI App     │    │  PostgreSQL DB   │  │
│  │  (Uvicorn)       │◀──▶│  (Managed)       │  │
│  │  Port: 8000      │    │                  │  │
│  └────────┬─────────┘    └─────────────────┘  │
│           │                                    │
└───────────┼────────────────────────────────────┘
            │ HTTPS
            ▼
┌───────────────────┐
│   GitHub API       │
│   api.github.com   │
└───────────────────┘

Environment Variables (set on platform):
- GITHUB_CLIENT_ID
- GITHUB_CLIENT_SECRET
- SECRET_KEY (cookie signing)
- ENCRYPTION_KEY (token encryption)
- DATABASE_URL (PostgreSQL connection string)
```

---

*Kết thúc Phase 2 — System Design. Tiếp theo: Phase 3 — Database Design.*
