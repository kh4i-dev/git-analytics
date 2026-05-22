# Module Documentation — Git Analytics

## 1. Module Core / Luồng xử lý chính

Xử lý business logic qua các Service class (OOP). Mỗi service đóng gói một nghiệp vụ.

```
app/services/
├── auth_service.py            # Xác thực GitHub OAuth
├── sync_service.py            # Đồng bộ repository (full/incremental)
├── sync_queue.py              # Worker queue bất đồng bộ
├── analytics_service.py       # Dashboard aggregation queries
├── insights_service.py        # Activity insights (time-of-day, streaks)
├── explore_service.py         # Duyệt repository
├── export_service.py          # Xuất PDF/Excel
├── engineering_report_service.py  # Tạo snapshot báo cáo
├── release_notes_service.py   # Release notes
├── changelog_service.py       # Changelog
├── risk_insight_service.py    # Risk insights
├── ai_provider_service.py     # Abstraction tầng AI (OpenAI/Gemini/Claude/NVIDIA)
├── ai_settings_service.py     # Quản lý cấu hình BYOK AI
```

**Luồng điển hình**: Route → Service → Repository → Model → DB

```python
# Ví dụ: SyncService
class SyncService:
    def __init__(self, db: Session, github_client: GitHubClient):
        self.db = db
        self.github_client = github_client
        self.repo_repo = RepositoryRepository(db)
        self.commit_repo = CommitRepository(db)

    def sync_repository(self, user: User, repo: Repository) -> SyncResult:
        if repo.last_synced_at is None:
            return self._full_sync(user, repo)  # First time
        return self._incremental_sync(user, repo)  # Since last_synced_at
```

---

## 2. Module CSDL

Kết nối database qua SQLAlchemy + Alembic migrations.

### Kết nối

```python
# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Models (11 ORM classes)

```
app/models/
├── user.py              # User — GitHub OAuth user
├── repository.py        # Repository — liên kết repo GitHub
├── contributor.py       # Contributor — người đóng góp
├── commit.py            # Commit — git commit
├── pull_request.py      # PullRequest — PR metadata
├── issue.py             # Issue — issue + labels (JSON)
├── branch.py            # Branch — nhánh repository
├── sync_job.py          # SyncJob — job đồng bộ
├── engineering_report.py  # EngineeringReport — snapshot báo cáo
├── ai_provider_setting.py # AiProviderSetting — BYOK credentials
├── ai_usage_event.py    # AiUsageEvent — audit log AI
```

### CRUD qua Repository Pattern

```python
# app/repositories/base.py
class BaseRepository[T]:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> T | None:
        return self.db.get(self.model_class, id)

    def list(self, **filters) -> list[T]:
        q = select(self.model_class)
        for k, v in filters.items():
            q = q.where(getattr(self.model_class, k) == v)
        return list(self.db.execute(q).scalars())

    def create(self, **data) -> T:
        obj = self.model_class(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
```

### Migrations (Alembic)

```
migrations/versions/
├── ceedab77b8b8_create_initial_tables.py
├── c4a8f2d1e9b0_add_sync_jobs.py
├── 394f452fcb07_add_default_branch_to_repositories.py
├── b6b2f7a0c9d1_add_multi_branch_analytics.py
├── d8a7f9c2b4e1_add_repository_engineering_reports.py
├── f3a1b2c4d5e6_add_ai_provider_settings.py
├── a6c4d9e8f1b2_add_ai_usage_events.py
├── 1f86d28b9afc_allow_nvidia_provider.py
```

```bash
alembic upgrade head   # Apply migrations
alembic revision --autogenerate -m "description"  # Tạo migration mới
```

---

## 3. Module Giao diện / Web

Server-side rendering với Jinja2 + Chart.js. FastAPI routers xử lý routing.

### Routing (FastAPI)

```python
# app/main.py — đăng ký router
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(repositories.router)
app.include_router(api_analytics.router, prefix="/api/v1")
app.include_router(api_ai.router, prefix="/api/v1")
# ... etc
```

### Dashboard Routes (HTML pages)

| Route | File | Mô tả |
|---|---|---|
| `/dashboard/overview` | `dashboard_overview.html` | Tổng quan |
| `/dashboard/commits` | `dashboard_commits.html` | Phân tích commits |
| `/dashboard/pull-requests` | `dashboard_pull_requests.html` | Phân tích PR |
| `/dashboard/issues` | `dashboard_issues.html` | Phân tích issues |
| `/dashboard/insights` | `dashboard_insights.html` | Activity insights |
| `/tools/release-notes` | `tools/release_notes.html` | Release notes |
| `/tools/changelog` | `tools/changelog.html` | Changelog |
| `/tools/risks` | `tools/risks.html` | Risk insights |

### API Routes (JSON endpoints)

| Route | File | Mô tả |
|---|---|---|
| `GET /api/v1/analytics/commits` | `api_analytics.py` | Dữ liệu commits |
| `GET /api/v1/analytics/pull-requests` | `api_analytics.py` | Dữ liệu PR |
| `GET /api/v1/analytics/issues` | `api_analytics.py` | Dữ liệu issues |
| `GET /api/v1/analytics/contributors` | `api_analytics.py` | Dữ liệu contributors |
| `GET /api/v1/analytics/heatmap` | `api_analytics.py` | Contribution heatmap |
| `GET /api/v1/analytics/kpi` | `api_analytics.py` | KPI scoring |
| `GET /api/v1/insights/time-of-day` | `api_insights.py` | Activity theo giờ |
| `GET /api/v1/insights/weekday` | `api_insights.py` | Activity theo ngày |
| `GET /api/v1/insights/streaks` | `api_insights.py` | Streaks |
| `POST /api/v1/ai/commit-message` | `api_ai.py` | Sinh commit message |
| `POST /api/v1/ai/review-pr` | `api_ai.py` | Review PR diff |
| `POST /api/v1/ai/ask` | `api_ai.py` | Repo Q&A |
| `POST /api/v1/sync/trigger` | `api_sync.py` | Kích hoạt đồng bộ |

### Frontend (Xử lý sự kiện)

```
static/
├── js/
│   ├── ai_tools.js          # AI workspace logic
│   ├── ai_assistant.js       # Chat assistant
│   ├── repo_context.js       # Chuyển đổi repo/branch
│   └── markdown_renderer.js  # Render markdown
└── css/
    └── ai_tools.css          # Styles AI tools
```

**Event handling flow**: Chart.js fetch → API → JSON → render chart

```javascript
// Ví dụ: fetch analytics data
async function loadCommits(repoId, branch) {
    const res = await fetch(`/api/v1/analytics/commits?repository_id=${repoId}&branch=${branch}`);
    const { data } = await res.json();
    renderChart(data);
}
```

---

## 4. Module API

Định nghĩa endpoint + gọi API từ client.

### Endpoint mẫu (FastAPI)

```python
# app/routes/api_analytics.py
from fastapi import APIRouter, Depends, Query
from app.services.analytics_service import AnalyticsService

router = APIRouter()

@router.get("/api/v1/analytics/commits")
def get_commits_analytics(
    repository_id: int = Query(...),
    branch: str = Query("main"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AnalyticsService(db)
    result = service.get_commit_stats(repository_id, branch)
    return success_response(result)
```

### Response format

```json
{
  "data": { ... },
  "error": null,
  "meta": {
    "trace_id": "abc-123",
    "timestamp": "2026-05-22T10:00:00Z"
  }
}
```

### Gọi API từ client (Python)

```python
import httpx

BASE_URL = "http://localhost:8000"
COOKIES = {"session": "..."}

def get_commit_stats(repo_id: int, branch: str = "main"):
    with httpx.Client(base_url=BASE_URL, cookies=COOKIES) as client:
        resp = client.get(
            "/api/v1/analytics/commits",
            params={"repository_id": repo_id, "branch": branch},
        )
        resp.raise_for_status()
        return resp.json()["data"]
```

### Gọi API từ frontend (JavaScript)

```javascript
async function getCommitStats(repoId, branch = "main") {
    const params = new URLSearchParams({ repository_id: repoId, branch });
    const res = await fetch(`/api/v1/analytics/commits?${params}`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    const json = await res.json();
    return json.data;
}
```

### GitHub API (qua GitHubClient)

```python
# app/clients/github_client.py
class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
        )

    async def get_commits(self, owner: str, repo: str, since: str | None = None):
        params = {"per_page": 100}
        if since:
            params["since"] = since
        return await self._paginated_get(f"/repos/{owner}/{repo}/commits", params)

    async def _paginated_get(self, path: str, params: dict):
        results = []
        while path:
            resp = await self.client.get(path, params=params)
            resp.raise_for_status()
            results.extend(resp.json())
            path = self._get_next_url(resp.headers.get("Link", ""))
            params = {}
        return results
```
