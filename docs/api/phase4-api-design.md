# Phase 4 — API Design

## 4.1 REST API Conventions

### Quy tắc chung

| Convention | Áp dụng |
|---|---|
| Base URL | `/api/v1/` |
| Naming | Lowercase, plural nouns: `/repositories`, `/commits` |
| HTTP Methods | GET (đọc), POST (tạo/action), DELETE (xóa) |
| Status Codes | Chuẩn HTTP semantics |
| Content Type | `application/json` |
| Authentication | Signed httpOnly cookie (tự động gửi bởi browser) |
| Versioning | URL prefix: `/api/v1/` |

### HTTP Status Codes

| Code | Ý nghĩa | Khi nào dùng |
|---|---|---|
| 200 | OK | GET thành công, action thành công |
| 201 | Created | POST tạo resource mới |
| 204 | No Content | DELETE thành công |
| 400 | Bad Request | Validation lỗi, thiếu parameter |
| 401 | Unauthorized | Chưa login hoặc token hết hạn |
| 403 | Forbidden | Không có quyền truy cập resource |
| 404 | Not Found | Resource không tồn tại |
| 409 | Conflict | Sync đang chạy, không thể sync lại |
| 429 | Too Many Requests | GitHub rate limit exceeded |
| 500 | Internal Server Error | Lỗi server không mong đợi |
| 502 | Bad Gateway | GitHub API trả lỗi |

---

## 4.2 API Versioning

### Strategy: URL Path Versioning

```
/api/v1/repositories
/api/v1/analytics/commits
```

**Lý do chọn URL versioning thay vì header versioning:**

| Tiêu chí | URL Path (`/api/v1/`) | Header (`Accept-Version: 1`) |
|---|---|---|
| Dễ hiểu | ✅ Nhìn URL biết version | Ẩn trong header |
| Test bằng browser | ✅ Gõ URL trực tiếp | Cần tool |
| Swagger UI | ✅ Hiển thị rõ | Phức tạp |
| Cache-friendly | ✅ URL khác = cache khác | Cần Vary header |
| Phù hợp MVP | ✅ | Quá phức tạp |

### Versioning Rules

- MVP chỉ có `v1` — không cần versioning phức tạp
- Nếu breaking change trong tương lai → tạo `/api/v2/` mới
- `/api/v1/` vẫn hoạt động song song (backward compatible)

---

## 4.3 Response Structure

### Standard Response Format

Mọi API response đều theo cấu trúc thống nhất:

**Success Response:**

```json
{
  "data": {
    "id": 1,
    "name": "my-repo",
    "full_name": "nguyenvan/my-repo"
  },
  "error": null,
  "meta": {
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

**Success Response (List):**

```json
{
  "data": [
    { "id": 1, "name": "repo-a" },
    { "id": 2, "name": "repo-b" }
  ],
  "error": null,
  "meta": {
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-15T10:30:00Z",
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 45,
      "total_pages": 3
    }
  }
}
```

**Error Response:**

```json
{
  "data": null,
  "error": {
    "code": "REPOSITORY_NOT_FOUND",
    "message": "Repository with id 99 not found.",
    "details": null
  },
  "meta": {
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Reasoning

| Field | Mục đích |
|---|---|
| `data` | Payload chính. Object hoặc array. Null khi lỗi |
| `error` | Null khi thành công. Object `{ code, message, details }` khi lỗi |
| `error.code` | Machine-readable error code (SCREAMING_SNAKE_CASE) |
| `error.message` | Human-readable message cho UI hoặc developer |
| `error.details` | Thông tin thêm (ví dụ: rate limit reset time, validation errors) |
| `meta.trace_id` | UUID để trace request qua logs |
| `meta.timestamp` | Thời điểm response (UTC ISO 8601) |
| `meta.pagination` | Chỉ có khi response là list |

### Error Codes

| Code | HTTP Status | Mô tả |
|---|---|---|
| `VALIDATION_ERROR` | 400 | Input không hợp lệ |
| `AUTHENTICATION_REQUIRED` | 401 | Chưa đăng nhập |
| `GITHUB_AUTH_FAILED` | 401 | GitHub token hết hạn/revoked |
| `FORBIDDEN` | 403 | Không có quyền |
| `REPOSITORY_NOT_FOUND` | 404 | Repo không tồn tại trong hệ thống |
| `SYNC_IN_PROGRESS` | 409 | Repo đang sync, không thể sync lại |
| `GITHUB_RATE_LIMIT_EXCEEDED` | 429 | Hết quota GitHub API |
| `SYNC_FAILED` | 500 | Sync thất bại do lỗi nội bộ |
| `GITHUB_API_ERROR` | 502 | GitHub API trả lỗi |
| `INTERNAL_ERROR` | 500 | Lỗi không xác định |

---

## 4.4 Pagination

### Strategy: Page-based Pagination

```
GET /api/v1/analytics/commits/list?repo_id=1&page=2&per_page=20
```

| Parameter | Default | Max | Mô tả |
|---|---|---|---|
| `page` | 1 | — | Trang hiện tại (1-indexed) |
| `per_page` | 20 | 100 | Số items mỗi trang |

### Pagination Response

```json
{
  "meta": {
    "pagination": {
      "page": 2,
      "per_page": 20,
      "total": 1250,
      "total_pages": 63
    }
  }
}
```

### Khi nào cần pagination

| Endpoint | Cần pagination | Lý do |
|---|---|---|
| Analytics (aggregated data) | ❌ | Trả về số liệu đã aggregate, luôn nhỏ |
| Recent commits list | ✅ | Có thể hàng nghìn commits |
| Recent PRs list | ✅ | Có thể hàng trăm PRs |
| Recent issues list | ✅ | Có thể hàng trăm issues |
| Repository list | ⚠️ | Thường < 20 repos, nhưng hỗ trợ để chuẩn |

### Không dùng Cursor-based Pagination

Cursor pagination (dùng `after=xxx`) phù hợp cho infinite scroll và dataset cực lớn. MVP dùng page-based vì:
- Đơn giản hơn
- UI dễ hiển thị "Page 2 of 63"
- Dataset nhỏ (individual developer)
- Dễ giải thích trong báo cáo

---

## 4.5 Rate Limiting (Application-level)

### MVP: Không cần application-level rate limiting

Lý do:
- Hệ thống MVP phục vụ 1 user
- Không public API cho third-party
- GitHub API rate limit đã được xử lý riêng ở GitHubClient

### Production Consideration

Nếu mở rộng cho nhiều users, cần thêm:

| Layer | Strategy |
|---|---|
| API endpoints | Token bucket: 100 requests/minute per user |
| Sync endpoint | Max 1 sync per repo at a time (đã có qua `SYNC_IN_PROGRESS`) |
| GitHub API calls | Per-user quota tracking |

### Sync Concurrency Limit (Đã implement)

```
POST /api/v1/repositories/{id}/sync

Nếu repo.last_sync_status = "syncing"
→ Return 409 { error: { code: "SYNC_IN_PROGRESS" } }
```

Đây là rate limiting ở mức business logic, không phải HTTP-level.

---

## 4.6 Validation Strategy

### Input Validation Layers

```
Request → Pydantic Schema → Route → Service → Repository → DB
          ▲                                              ▲
          │                                              │
     Type + format                              Constraint check
     validation                                 (unique, FK, etc.)
```

### Validation Rules

| Layer | Validates | Tool |
|---|---|---|
| Pydantic Schema | Type, format, required fields, min/max | Pydantic BaseModel |
| Route | Request structure, query params | FastAPI + Pydantic |
| Service | Business rules (repo belongs to user, sync not running) | Manual checks → Domain Exception |
| Database | Unique constraints, FK, NOT NULL | SQLAlchemy + DB engine |

### Ví dụ Validation

**Query Parameter Validation:**

```
GET /api/v1/analytics/commits?repo_id=abc
→ 400 { error: { code: "VALIDATION_ERROR", message: "repo_id must be integer" } }

GET /api/v1/analytics/commits?repo_id=1&page=-1
→ 400 { error: { code: "VALIDATION_ERROR", message: "page must be >= 1" } }
```

**Business Rule Validation:**

```
POST /api/v1/repositories/99/sync
(repo 99 thuộc user khác)
→ 404 { error: { code: "REPOSITORY_NOT_FOUND" } }

POST /api/v1/repositories/1/sync
(repo 1 đang sync)
→ 409 { error: { code: "SYNC_IN_PROGRESS" } }
```

### Pydantic Schemas (Key schemas)

| Schema | Fields | Used by |
|---|---|---|
| `RepositoryOut` | id, full_name, language, is_private, last_synced_at, last_sync_status | GET /repositories |
| `SyncResponse` | status, message, synced_counts | POST /sync |
| `CommitStatsOut` | commits_per_day[], commits_by_author[], total_commits | GET /analytics/commits |
| `PRStatsOut` | pr_by_state{}, avg_merge_time, prs_by_author[] | GET /analytics/pulls |
| `IssueStatsOut` | issues_by_state{}, issues_by_label{}, avg_close_time | GET /analytics/issues |
| `OverviewStatsOut` | total_commits, total_prs, open_issues, last_sync | GET /analytics/overview |

---

## 4.7 Authentication Middleware

### Request Flow

```
Browser Request
    │
    ▼
┌──────────────────────┐
│   Cookie Middleware    │
│   Read signed cookie  │
│   Extract user_id     │
└──────────┬───────────┘
           │
    ┌──────▼──────┐
    │ user_id     │
    │ present?    │
    └──┬──────┬───┘
       │      │
      Yes     No
       │      │
       ▼      ▼
  ┌────────┐  ┌────────────────────────┐
  │ Lookup │  │ Page route → redirect  │
  │ user   │  │   /auth/login          │
  │ in DB  │  │ API route → 401 JSON   │
  └───┬────┘  └────────────────────────┘
      │
  ┌───▼────┐
  │ Found? │
  └─┬────┬─┘
   Yes   No
    │     │
    ▼     ▼
 ┌──────┐ ┌────────────┐
 ┌Attach│ │Clear cookie│
 │user  │ │Redirect    │
 │to req│ │/auth/login │
 └──┬───┘ └────────────┘
    │
    ▼
  Route Handler
  (request.state.current_user available)
```

### Protected vs Public Routes

| Route | Auth Required | Mô tả |
|---|---|---|
| `GET /auth/login` | ❌ | Login page |
| `GET /auth/github/callback` | ❌ | OAuth callback |
| `POST /auth/logout` | ✅ | Logout |
| `GET /dashboard/*` | ✅ | Dashboard pages |
| `GET /repositories/*` | ✅ | Repository pages |
| `GET /api/v1/*` | ✅ | All API endpoints |
| `POST /api/v1/*` | ✅ | All API endpoints |

### Token Decryption

Token chỉ được decrypt khi service cần gọi GitHub API:

```
Route → Service → need GitHub data → decrypt token → GitHubClient
                                         ▲
                                         │
                              Only here, only in memory
                              Never stored decrypted
                              Never passed to response
```

---

## 4.8 API Endpoint List

### Auth Routes (không có prefix /api/v1)

| Method | Path | Mô tả | Response |
|---|---|---|---|
| GET | `/auth/login` | Redirect đến GitHub OAuth | 302 → GitHub |
| GET | `/auth/github/callback` | OAuth callback, tạo session | 302 → /dashboard |
| POST | `/auth/logout` | Xóa session, clear cookie | 302 → /auth/login |

---

### Repository Endpoints

| Method | Path | Mô tả | Response |
|---|---|---|---|
| GET | `/api/v1/repositories` | Danh sách repos đã kết nối | `{ data: [RepositoryOut] }` |
| GET | `/api/v1/repositories/github` | Danh sách repos từ GitHub (chưa kết nối) | `{ data: [GitHubRepoOut] }` |
| POST | `/api/v1/repositories` | Kết nối 1 repo vào hệ thống | `{ data: RepositoryOut }` 201 |
| GET | `/api/v1/repositories/{id}` | Chi tiết 1 repo đã kết nối | `{ data: RepositoryOut }` |
| DELETE | `/api/v1/repositories/{id}` | Ngắt kết nối + xóa data | 204 No Content |

**POST /api/v1/repositories — Request Body:**

```json
{
  "github_repo_id": 123456,
  "owner": "nguyenvan",
  "name": "my-project",
  "full_name": "nguyenvan/my-project",
  "description": "My awesome project",
  "language": "Python",
  "is_private": true,
  "html_url": "https://github.com/nguyenvan/my-project"
}
```

---

### Sync Endpoints

| Method | Path | Mô tả | Response |
|---|---|---|---|
| POST | `/api/v1/repositories/{id}/sync` | Bắt đầu sync repo | `{ data: SyncResponse }` |
| GET | `/api/v1/repositories/{id}/sync/status` | Trạng thái sync hiện tại | `{ data: SyncStatusOut }` |
| GET | `/api/v1/github/rate-limit` | Kiểm tra GitHub API quota | `{ data: RateLimitOut }` |

**POST /api/v1/repositories/{id}/sync — Response:**

```json
{
  "data": {
    "status": "completed",
    "message": "Sync completed successfully",
    "synced": {
      "commits": 150,
      "pull_requests": 12,
      "issues": 8,
      "contributors": 5
    },
    "duration_seconds": 3.2
  },
  "error": null,
  "meta": { "trace_id": "...", "timestamp": "..." }
}
```

**GET /api/v1/github/rate-limit — Response:**

```json
{
  "data": {
    "limit": 5000,
    "remaining": 4523,
    "reset_at": "2024-01-15T11:00:00Z",
    "minutes_until_reset": 28
  },
  "error": null,
  "meta": { "trace_id": "...", "timestamp": "..." }
}
```

---

### Analytics Endpoints

| Method | Path | Mô tả | Response |
|---|---|---|---|
| GET | `/api/v1/analytics/overview` | Tổng quan repo | `{ data: OverviewStatsOut }` |
| GET | `/api/v1/analytics/commits` | Thống kê commits | `{ data: CommitStatsOut }` |
| GET | `/api/v1/analytics/pulls` | Thống kê pull requests | `{ data: PRStatsOut }` |
| GET | `/api/v1/analytics/issues` | Thống kê issues | `{ data: IssueStatsOut }` |

**Tất cả analytics endpoints đều yêu cầu query parameter:**

```
?repo_id=1
```

---

**GET /api/v1/analytics/overview?repo_id=1 — Response:**

```json
{
  "data": {
    "repository": {
      "full_name": "nguyenvan/my-project",
      "language": "Python",
      "is_private": true,
      "last_synced_at": "2024-01-15T10:00:00Z"
    },
    "summary": {
      "total_commits": 1250,
      "total_pull_requests": 45,
      "total_issues": 32,
      "open_issues": 8,
      "total_contributors": 5
    },
    "activity_timeline": [
      { "date": "2024-01-01", "commits": 5, "prs": 1, "issues": 0 },
      { "date": "2024-01-02", "commits": 8, "prs": 0, "issues": 2 }
    ]
  }
}
```

---

**GET /api/v1/analytics/commits?repo_id=1 — Response:**

```json
{
  "data": {
    "total_commits": 1250,
    "commits_per_day": [
      { "date": "2024-01-01", "count": 5 },
      { "date": "2024-01-02", "count": 8 }
    ],
    "commits_by_author": [
      { "author": "nguyenvan", "avatar_url": "...", "count": 800 },
      { "author": "contributor2", "avatar_url": "...", "count": 350 }
    ],
    "recent_commits": [
      {
        "sha": "abc123",
        "short_sha": "abc123",
        "message": "fix login bug",
        "author_login": "nguyenvan",
        "committed_at": "2024-01-15T09:30:00Z",
        "html_url": "https://github.com/..."
      }
    ]
  }
}
```

---

**GET /api/v1/analytics/pulls?repo_id=1 — Response:**

```json
{
  "data": {
    "total_pull_requests": 45,
    "by_state": {
      "open": 3,
      "closed": 12,
      "merged": 30
    },
    "avg_merge_time_hours": 18.5,
    "merge_time_trend": [
      { "month": "2024-01", "avg_hours": 12.3 },
      { "month": "2023-12", "avg_hours": 24.1 }
    ],
    "prs_by_author": [
      { "author": "nguyenvan", "count": 30, "merged": 25 },
      { "author": "contributor2", "count": 15, "merged": 5 }
    ],
    "recent_pull_requests": [
      {
        "number": 42,
        "title": "Add login feature",
        "state": "merged",
        "author_login": "nguyenvan",
        "created_at": "2024-01-10T08:00:00Z",
        "merged_at": "2024-01-11T14:30:00Z",
        "html_url": "https://github.com/..."
      }
    ]
  }
}
```

---

**GET /api/v1/analytics/issues?repo_id=1 — Response:**

```json
{
  "data": {
    "total_issues": 32,
    "by_state": {
      "open": 8,
      "closed": 24
    },
    "avg_close_time_hours": 72.4,
    "by_label": [
      { "label": "bug", "count": 12 },
      { "label": "enhancement", "count": 8 },
      { "label": "documentation", "count": 5 }
    ],
    "issues_timeline": [
      { "date": "2024-01-01", "opened": 2, "closed": 1 },
      { "date": "2024-01-02", "opened": 0, "closed": 3 }
    ],
    "recent_issues": [
      {
        "number": 15,
        "title": "Login button not working",
        "state": "open",
        "author_login": "nguyenvan",
        "labels": ["bug", "high-priority"],
        "created_at": "2024-01-14T16:00:00Z",
        "html_url": "https://github.com/..."
      }
    ]
  }
}
```

---

### Page Routes (Jinja2, không phải API)

| Method | Path | Mô tả | Template |
|---|---|---|---|
| GET | `/` | Landing / redirect | → /dashboard hoặc /auth/login |
| GET | `/dashboard` | Overview page | dashboard/overview.html |
| GET | `/dashboard/commits` | Commits analytics page | dashboard/commits.html |
| GET | `/dashboard/pulls` | PR analytics page | dashboard/pulls.html |
| GET | `/dashboard/issues` | Issues analytics page | dashboard/issues.html |
| GET | `/repositories` | Repository management page | repositories/list.html |

Page routes trả HTML skeleton. JavaScript trong template gọi `/api/v1/analytics/*` để lấy data cho Chart.js.

---

## 4.9 API Endpoint Summary Table

| # | Method | Endpoint | Auth | Response | Mô tả |
|---|---|---|---|---|---|
| 1 | GET | `/auth/login` | ❌ | 302 | Redirect GitHub OAuth |
| 2 | GET | `/auth/github/callback` | ❌ | 302 | OAuth callback |
| 3 | POST | `/auth/logout` | ✅ | 302 | Logout |
| 4 | GET | `/api/v1/repositories` | ✅ | 200 JSON | List connected repos |
| 5 | GET | `/api/v1/repositories/github` | ✅ | 200 JSON | List GitHub repos |
| 6 | POST | `/api/v1/repositories` | ✅ | 201 JSON | Connect repo |
| 7 | GET | `/api/v1/repositories/{id}` | ✅ | 200 JSON | Repo detail |
| 8 | DELETE | `/api/v1/repositories/{id}` | ✅ | 204 | Disconnect repo |
| 9 | POST | `/api/v1/repositories/{id}/sync` | ✅ | 200 JSON | Start sync |
| 10 | GET | `/api/v1/repositories/{id}/sync/status` | ✅ | 200 JSON | Sync status |
| 11 | GET | `/api/v1/github/rate-limit` | ✅ | 200 JSON | Rate limit info |
| 12 | GET | `/api/v1/analytics/overview` | ✅ | 200 JSON | Overview stats |
| 13 | GET | `/api/v1/analytics/commits` | ✅ | 200 JSON | Commit stats |
| 14 | GET | `/api/v1/analytics/pulls` | ✅ | 200 JSON | PR stats |
| 15 | GET | `/api/v1/analytics/issues` | ✅ | 200 JSON | Issue stats |

**Tổng cộng: 15 endpoints** (3 auth + 5 repository + 3 sync + 4 analytics)

---

## 4.10 Swagger UI

FastAPI tự động generate Swagger UI tại `/docs`:

```
http://localhost:8000/docs
```

Swagger UI cho phép:
- Xem tất cả endpoints, parameters, response schemas
- Test API trực tiếp trên browser
- Export OpenAPI spec (JSON/YAML) cho documentation

Đây là điểm mạnh của FastAPI — **không cần viết API docs riêng**, Swagger tự generate từ code + Pydantic schemas.

### Swagger Tags

Endpoints được nhóm theo tags:

| Tag | Endpoints |
|---|---|
| Auth | /auth/* |
| Repositories | /api/v1/repositories/* |
| Sync | /api/v1/repositories/*/sync, /api/v1/github/rate-limit |
| Analytics | /api/v1/analytics/* |
