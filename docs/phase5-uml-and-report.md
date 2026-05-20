# Phase 5 — UML & Report Mapping

## 5.1 Use Case Diagram

```mermaid
graph TB
    subgraph "Hệ thống Git Analytics"
        UC01["UC-01: Đăng nhập GitHub OAuth"]
        UC02["UC-02: Xem danh sách repositories"]
        UC03["UC-03: Kết nối repository"]
        UC04["UC-04: Đồng bộ dữ liệu repository"]
        UC05["UC-05: Xem Dashboard Overview"]
        UC06["UC-06: Xem Commit Analytics"]
        UC07["UC-07: Xem Pull Request Analytics"]
        UC08["UC-08: Xem Issue Analytics"]
        UC09["UC-09: Đăng xuất"]
        UC10["UC-10: Kiểm tra Rate Limit"]
        UC11["UC-11: Ngắt kết nối repository"]
    end

    User((User / Developer))
    GitHub[(GitHub API)]

    User --> UC01
    User --> UC02
    User --> UC03
    User --> UC04
    User --> UC05
    User --> UC06
    User --> UC07
    User --> UC08
    User --> UC09
    User --> UC10
    User --> UC11

    UC01 -.->|<<include>>| GitHub
    UC02 -.->|<<include>>| GitHub
    UC04 -.->|<<include>>| GitHub
    UC04 -.->|<<include>>| UC10
```

### Use Case Description Table

| UC | Tên | Actor | Precondition | Postcondition |
|---|---|---|---|---|
| UC-01 | Đăng nhập GitHub OAuth | User | Chưa có session | Session tạo, token lưu encrypted |
| UC-02 | Xem danh sách repositories | User | Đã đăng nhập | Hiển thị repos từ GitHub + đã kết nối |
| UC-03 | Kết nối repository | User | Đã đăng nhập, chọn repo | Repo lưu vào DB, status = pending |
| UC-04 | Đồng bộ dữ liệu | User | Repo đã kết nối, quota đủ | Data sync vào DB, status = success |
| UC-05 | Xem Dashboard Overview | User | Repo đã sync ≥ 1 lần | Hiển thị summary cards + charts |
| UC-06 | Xem Commit Analytics | User | Repo đã sync | Hiển thị commit charts + tables |
| UC-07 | Xem PR Analytics | User | Repo đã sync | Hiển thị PR charts + tables |
| UC-08 | Xem Issue Analytics | User | Repo đã sync | Hiển thị issue charts + tables |
| UC-09 | Đăng xuất | User | Đã đăng nhập | Session xóa, cookie clear |
| UC-10 | Kiểm tra Rate Limit | User | Đã đăng nhập | Hiển thị remaining quota |
| UC-11 | Ngắt kết nối repository | User | Repo đã kết nối | Repo + data bị xóa khỏi DB |

---

## 5.2 Class Diagram

```mermaid
classDiagram
    class User {
        +int id
        +int github_id
        +str github_login
        +str name
        +str avatar_url
        +str encrypted_github_token
        +datetime last_login_at
        +datetime created_at
        +datetime updated_at
    }

    class Repository {
        +int id
        +int user_id
        +int github_repo_id
        +str owner
        +str name
        +str full_name
        +str description
        +str language
        +bool is_private
        +str html_url
        +datetime last_synced_at
        +str last_sync_status
        +str last_sync_error
        +datetime sync_started_at
        +datetime created_at
        +datetime updated_at
    }

    class Contributor {
        +int id
        +int repo_id
        +str github_login
        +str email
        +str display_name
        +str avatar_url
        +str source_type
        +datetime created_at
        +datetime updated_at
    }

    class Commit {
        +int id
        +int repo_id
        +int contributor_id
        +str sha
        +str message
        +str author_name
        +str author_email
        +str author_login
        +datetime committed_at
        +str html_url
        +datetime created_at
    }

    class PullRequest {
        +int id
        +int repo_id
        +int contributor_id
        +int number
        +str title
        +str state
        +bool is_merged
        +str author_login
        +bool draft
        +datetime created_at
        +datetime updated_at
        +datetime closed_at
        +datetime merged_at
        +str html_url
    }

    class Issue {
        +int id
        +int repo_id
        +int contributor_id
        +int number
        +str title
        +str state
        +str author_login
        +json labels
        +datetime created_at
        +datetime updated_at
        +datetime closed_at
        +str html_url
    }

    class AuthService {
        +build_oauth_url() str
        +handle_callback(code) User
        +encrypt_token(token) str
        +decrypt_token(encrypted) str
        +logout(user_id) void
    }

    class SyncService {
        +sync_repository(repo_id, user) SyncResult
        -determine_sync_mode(repo) str
        -sync_commits(repo, since) int
        -sync_pull_requests(repo, since) int
        -sync_issues(repo, since) int
        -resolve_contributor(author_data, repo_id) Contributor
    }

    class AnalyticsService {
        +get_overview(repo_id) OverviewStats
        +get_commit_stats(repo_id) CommitStats
        +get_pr_stats(repo_id) PRStats
        +get_issue_stats(repo_id) IssueStats
    }

    class GitHubClient {
        -str base_url
        -str access_token
        +get_user() dict
        +get_repositories() list
        +get_commits(owner, repo, since) list
        +get_pulls(owner, repo, since) list
        +get_issues(owner, repo, since) list
        +get_rate_limit() dict
        -paginate(url, params) list
        -handle_response(response) dict
    }

    class UserRepo {
        +get_by_id(id) User
        +get_by_github_id(github_id) User
        +upsert(user_data) User
        +delete(id) void
    }

    class RepositoryRepo {
        +get_by_id(id) Repository
        +get_by_user(user_id) list
        +create(repo_data) Repository
        +update_sync_status(id, status, error) void
        +delete(id) void
    }

    class CommitRepo {
        +upsert_many(commits) int
        +get_by_repo(repo_id, page, per_page) list
        +count_by_date(repo_id) list
        +count_by_author(repo_id) list
    }

    class PullRequestRepo {
        +upsert_many(prs) int
        +get_by_repo(repo_id, page, per_page) list
        +count_by_state(repo_id) dict
        +avg_merge_time(repo_id) float
    }

    class IssueRepo {
        +upsert_many(issues) int
        +get_by_repo(repo_id, page, per_page) list
        +count_by_state(repo_id) dict
        +avg_close_time(repo_id) float
    }

    User "1" --> "*" Repository : owns
    Repository "1" --> "*" Contributor : has
    Repository "1" --> "*" Commit : contains
    Repository "1" --> "*" PullRequest : contains
    Repository "1" --> "*" Issue : contains
    Contributor "1" --> "*" Commit : authored
    Contributor "1" --> "*" PullRequest : authored
    Contributor "1" --> "*" Issue : authored

    AuthService ..> UserRepo : uses
    AuthService ..> GitHubClient : uses
    SyncService ..> GitHubClient : uses
    SyncService ..> RepositoryRepo : uses
    SyncService ..> CommitRepo : uses
    SyncService ..> PullRequestRepo : uses
    SyncService ..> IssueRepo : uses
    AnalyticsService ..> CommitRepo : uses
    AnalyticsService ..> PullRequestRepo : uses
    AnalyticsService ..> IssueRepo : uses
```

### Class Responsibility Summary

| Class | Layer | Responsibility |
|---|---|---|
| User, Repository, Contributor, Commit, PullRequest, Issue | Model | Định nghĩa bảng, columns, relationships |
| AuthService | Service | OAuth flow, token encrypt/decrypt, session |
| SyncService | Service | Điều phối sync, quyết định full/incremental |
| AnalyticsService | Service | SQL aggregation, trả dashboard data |
| GitHubClient | Client | HTTP calls đến GitHub, pagination, rate limit |
| UserRepo, RepositoryRepo, CommitRepo, ... | Repository | CRUD, upsert, aggregation queries |

---

## 5.3 Sequence Diagrams

### Sequence 1: Đăng nhập GitHub OAuth

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant FastAPI
    participant AuthService
    participant GitHubClient
    participant GitHub as GitHub API
    participant UserRepo
    participant DB as Database

    User->>Browser: Click "Login with GitHub"
    Browser->>FastAPI: GET /auth/login
    FastAPI->>AuthService: build_oauth_url()
    AuthService-->>FastAPI: OAuth URL + state token
    FastAPI-->>Browser: 302 Redirect to GitHub

    Browser->>GitHub: Authorize app (scope: repo, read:user)
    User->>GitHub: Approve permissions
    GitHub-->>Browser: 302 Redirect /auth/github/callback?code=xxx&state=yyy

    Browser->>FastAPI: GET /auth/github/callback?code=xxx&state=yyy
    FastAPI->>AuthService: handle_callback(code, state)
    AuthService->>AuthService: Verify state (CSRF)
    AuthService->>GitHub: POST /login/oauth/access_token {code}
    GitHub-->>AuthService: access_token
    AuthService->>GitHubClient: get_user(token)
    GitHubClient->>GitHub: GET /user
    GitHub-->>GitHubClient: {github_id, login, name, avatar}
    GitHubClient-->>AuthService: user_data
    AuthService->>AuthService: encrypt_token(access_token)
    AuthService->>UserRepo: upsert(user_data + encrypted_token)
    UserRepo->>DB: INSERT/UPDATE users
    DB-->>UserRepo: user record
    UserRepo-->>AuthService: User object
    AuthService-->>FastAPI: User object
    FastAPI->>FastAPI: Set signed cookie {user_id}
    FastAPI-->>Browser: 302 Redirect /dashboard
```

### Sequence 2: Đồng bộ Repository

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant FastAPI
    participant SyncService
    participant GitHubClient
    participant GitHub as GitHub API
    participant RepoRepo as RepositoryRepo
    participant CommitRepo
    participant PRRepo as PullRequestRepo
    participant IssueRepo
    participant DB as Database

    User->>Browser: Click "Sync" button
    Browser->>FastAPI: POST /api/v1/repositories/1/sync
    FastAPI->>FastAPI: Verify auth cookie
    FastAPI->>SyncService: sync_repository(repo_id=1, user)

    SyncService->>RepoRepo: get_by_id(1)
    RepoRepo->>DB: SELECT * FROM repositories WHERE id=1
    DB-->>RepoRepo: repository record
    RepoRepo-->>SyncService: Repository (last_synced_at=null)

    SyncService->>SyncService: Check status != "syncing"
    SyncService->>RepoRepo: update_sync_status("syncing")

    SyncService->>GitHubClient: get_rate_limit()
    GitHubClient->>GitHub: GET /rate_limit
    GitHub-->>GitHubClient: {remaining: 4500}
    GitHubClient-->>SyncService: remaining=4500 (OK)

    Note over SyncService: last_synced_at=null → Full Sync

    SyncService->>GitHubClient: get_commits(owner, repo)
    GitHubClient->>GitHub: GET /repos/owner/repo/commits?per_page=100
    GitHub-->>GitHubClient: commits page 1
    GitHubClient->>GitHub: GET ...?page=2
    GitHub-->>GitHubClient: commits page 2 (last)
    GitHubClient-->>SyncService: all commits

    SyncService->>GitHubClient: get_pulls(owner, repo)
    GitHubClient->>GitHub: GET /repos/owner/repo/pulls?state=all&per_page=100
    GitHub-->>GitHubClient: all PRs
    GitHubClient-->>SyncService: all PRs

    SyncService->>GitHubClient: get_issues(owner, repo)
    GitHubClient->>GitHub: GET /repos/owner/repo/issues?state=all&per_page=100
    GitHub-->>GitHubClient: all issues (filtered: exclude PRs)
    GitHubClient-->>SyncService: all issues

    SyncService->>SyncService: Resolve contributors
    SyncService->>CommitRepo: upsert_many(commits)
    CommitRepo->>DB: INSERT ON CONFLICT UPDATE
    SyncService->>PRRepo: upsert_many(prs)
    PRRepo->>DB: INSERT ON CONFLICT UPDATE
    SyncService->>IssueRepo: upsert_many(issues)
    IssueRepo->>DB: INSERT ON CONFLICT UPDATE

    SyncService->>RepoRepo: update_sync_status("success", last_synced_at=now())
    RepoRepo->>DB: UPDATE repositories

    SyncService-->>FastAPI: SyncResult {commits: 150, prs: 12, issues: 8}
    FastAPI-->>Browser: 200 JSON response
    Browser->>Browser: Show success notification
```

### Sequence 3: Xem Commit Analytics

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant FastAPI
    participant AnalyticsService
    participant CommitRepo
    participant DB as Database

    User->>Browser: Click "Commits" menu
    Browser->>FastAPI: GET /dashboard/commits?repo_id=1
    FastAPI->>FastAPI: Verify auth cookie
    FastAPI-->>Browser: HTML skeleton (layout + loading spinners)

    Browser->>FastAPI: fetch GET /api/v1/analytics/commits?repo_id=1
    FastAPI->>AnalyticsService: get_commit_stats(repo_id=1)

    AnalyticsService->>CommitRepo: count_by_date(repo_id=1)
    CommitRepo->>DB: SELECT DATE(committed_at), COUNT(*) FROM commits WHERE repo_id=1 GROUP BY DATE(committed_at)
    DB-->>CommitRepo: [{date, count}, ...]
    CommitRepo-->>AnalyticsService: commits_per_day

    AnalyticsService->>CommitRepo: count_by_author(repo_id=1)
    CommitRepo->>DB: SELECT author_login, COUNT(*) FROM commits WHERE repo_id=1 GROUP BY author_login
    DB-->>CommitRepo: [{author, count}, ...]
    CommitRepo-->>AnalyticsService: commits_by_author

    AnalyticsService->>CommitRepo: get_by_repo(repo_id=1, limit=10)
    CommitRepo->>DB: SELECT * FROM commits WHERE repo_id=1 ORDER BY committed_at DESC LIMIT 10
    DB-->>CommitRepo: recent commits
    CommitRepo-->>AnalyticsService: recent_commits

    AnalyticsService-->>FastAPI: CommitStats
    FastAPI-->>Browser: 200 JSON {data: {commits_per_day, commits_by_author, recent_commits}}

    Browser->>Browser: Chart.js renders commits/day line chart
    Browser->>Browser: Chart.js renders commits by author bar chart
    Browser->>Browser: Render recent commits table
```

---

## 5.4 Activity Diagram

### Activity: Sync Repository

```mermaid
flowchart TD
    A[User nhấn Sync] --> B{Đã đăng nhập?}
    B -->|Không| C[Redirect Login]
    B -->|Có| D{Repo thuộc user?}
    D -->|Không| E[404 Not Found]
    D -->|Có| F{Đang sync?}
    F -->|Có| G[409 Sync In Progress]
    F -->|Không| H[Gọi GET /rate_limit]

    H --> I{Remaining >= 50?}
    I -->|Không| J[429 Rate Limit Low - Cảnh báo user]
    I -->|Có| K[Set status = syncing]

    K --> L{last_synced_at = null?}
    L -->|Có| M[Full Sync mode]
    L -->|Không| N[Incremental Sync mode]

    M --> O[Fetch commits từ GitHub]
    N --> O

    O --> P{API Error?}
    P -->|403 Rate Limit| Q[Set status = failed, lưu error]
    P -->|Lỗi khác| Q
    P -->|OK| R[Fetch pull requests]

    R --> S{API Error?}
    S -->|Lỗi| Q
    S -->|OK| T[Fetch issues]

    T --> U{API Error?}
    U -->|Lỗi| Q
    U -->|OK| V[Resolve contributors]

    V --> W[Upsert commits vào DB]
    W --> X[Upsert PRs vào DB]
    X --> Y[Upsert issues vào DB]

    Y --> Z{DB Error?}
    Z -->|Lỗi| Q
    Z -->|OK| AA[Set status = success]

    AA --> AB[Update last_synced_at = now]
    AB --> AC[Return SyncResult]
    Q --> AD[Return Error Response]
```

### Activity: Xem Dashboard

```mermaid
flowchart TD
    A[User mở Dashboard page] --> B{Đã đăng nhập?}
    B -->|Không| C[Redirect /auth/login]
    B -->|Có| D[Server trả HTML skeleton]

    D --> E[Browser hiển thị layout + loading]
    E --> F[JavaScript gọi API analytics]

    F --> G{API trả lỗi?}
    G -->|401| H[Redirect login]
    G -->|404| I[Hiển thị: Chưa chọn repo]
    G -->|500| J[Hiển thị: Error message]
    G -->|200 OK| K[Nhận JSON data]

    K --> L[Chart.js render biểu đồ]
    L --> M[Render data tables]
    M --> N[Dashboard hiển thị hoàn chỉnh]
```

---

## 5.5 Deployment Diagram

```mermaid
graph TB
    subgraph "Client"
        Browser["Web Browser<br/>(Chrome, Firefox)"]
    end

    subgraph "Cloud Platform (Railway / Render)"
        subgraph "Application Server"
            Uvicorn["Uvicorn ASGI Server<br/>Port 8000"]
            FastAPI["FastAPI Application"]
            Jinja2["Jinja2 Templates"]
            Static["Static Files<br/>(CSS, JS, Images)"]
        end

        subgraph "Database Server"
            PostgreSQL["PostgreSQL 15<br/>(Managed)"]
        end
    end

    subgraph "External Services"
        GitHubAPI["GitHub REST API<br/>api.github.com"]
        GitHubOAuth["GitHub OAuth<br/>github.com/login/oauth"]
    end

    Browser -->|HTTPS| Uvicorn
    Uvicorn --> FastAPI
    FastAPI --> Jinja2
    FastAPI --> Static
    FastAPI -->|SQLAlchemy| PostgreSQL
    FastAPI -->|httpx HTTPS| GitHubAPI
    FastAPI -->|httpx HTTPS| GitHubOAuth
    Browser -->|OAuth Redirect| GitHubOAuth
```

### Deployment Components

| Component | Technology | Mô tả |
|---|---|---|
| ASGI Server | Uvicorn | Chạy FastAPI application |
| Application | FastAPI + Python 3.11+ | Business logic, API, templates |
| Database | PostgreSQL 15 (managed) | Data persistence |
| Static Files | Served by FastAPI | CSS, JS, images |
| TLS/HTTPS | Platform-provided | Mã hóa traffic |
| DNS | Platform-provided | Custom domain (optional) |

### Environment Variables (Production)

| Variable | Mô tả | Ví dụ |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host:5432/dbname` |
| `GITHUB_CLIENT_ID` | OAuth App Client ID | `Iv1.abc123...` |
| `GITHUB_CLIENT_SECRET` | OAuth App Client Secret | `secret_xxx...` |
| `SECRET_KEY` | Cookie signing key | Random 32+ chars |
| `ENCRYPTION_KEY` | Fernet key cho token | Base64 32-byte key |
| `ENVIRONMENT` | dev / production | `production` |
| `ALLOWED_ORIGINS` | CORS origins | `https://myapp.railway.app` |

---

## 5.6 Report Mapping — Cấu trúc báo cáo đồ án

### Chương 1: Tổng quan đề tài

| Mục | Nội dung | Lấy từ |
|---|---|---|
| 1.1 Đặt vấn đề | Bối cảnh, pain points, nhu cầu thực tế | Phase 1 §1.1, §1.2 |
| 1.2 Mục tiêu đề tài | Xây dựng hệ thống Git Analytics | Phase 1 §1.1 |
| 1.3 Phạm vi đề tài | MVP scope, out-of-scope | Phase 1 §1.7 |
| 1.4 Đối tượng sử dụng | User personas | Phase 1 §1.3 |
| 1.5 Phương pháp nghiên cứu | Phân tích, thiết kế, triển khai | — |
| 1.6 Công cụ & công nghệ | Tech stack, lý do chọn | Phase 2 §2.2, §2.11 |

### Chương 2: Cơ sở lý thuyết

| Mục | Nội dung | Lấy từ |
|---|---|---|
| 2.1 Tổng quan về GitHub API | REST API, authentication, rate limiting | Phase 2 §2.6 |
| 2.2 OAuth 2.0 | Giải thích OAuth flow, scopes | Phase 2 §2.7, ADR-0001 |
| 2.3 Kiến trúc Layered Architecture | 3-layer, separation of concerns | Phase 2 §2.1, §2.3 |
| 2.4 Design Patterns | Repository Pattern, Adapter Pattern, Service Layer | Phase 2 §2.3 |
| 2.5 RESTful API Design | Conventions, response format, pagination | Phase 4 §4.1-§4.4 |
| 2.6 Các công nghệ sử dụng | FastAPI, SQLAlchemy, Chart.js, etc. | Phase 2 §2.11 |

### Chương 3: Phân tích & Thiết kế

| Mục | Nội dung | Lấy từ |
|---|---|---|
| 3.1 Phân tích yêu cầu | FR, NFR tables | Phase 1 §1.5, §1.6 |
| 3.2 Use Case Diagram | Diagram + mô tả UC | Phase 5 §5.1 |
| 3.3 Class Diagram | Entity + Service classes | Phase 5 §5.2 |
| 3.4 Sequence Diagrams | Login, Sync, Dashboard flows | Phase 5 §5.3 |
| 3.5 Activity Diagrams | Sync flow, Dashboard flow | Phase 5 §5.4 |
| 3.6 Thiết kế database | ERD, table design, index strategy | Phase 3 §3.1-§3.5 |
| 3.7 Thiết kế API | Endpoint list, response format | Phase 4 §4.8, §4.3 |
| 3.8 Kiến trúc hệ thống | Architecture overview, module boundaries | Phase 2 §2.1, §2.3, §2.4 |
| 3.9 Deployment Diagram | Cloud deployment | Phase 5 §5.5 |

### Chương 4: Triển khai & Kết quả

| Mục | Nội dung | Nguồn |
|---|---|---|
| 4.1 Cài đặt môi trường | Python, pip, PostgreSQL, env setup | README.md |
| 4.2 Triển khai chức năng | Screenshot từng feature | Chụp từ app |
| 4.2.1 Đăng nhập GitHub | Screenshot login flow | App |
| 4.2.2 Quản lý Repository | Screenshot repo list, connect | App |
| 4.2.3 Đồng bộ dữ liệu | Screenshot sync process, status | App |
| 4.2.4 Dashboard Overview | Screenshot overview page | App |
| 4.2.5 Commit Analytics | Screenshot charts | App |
| 4.2.6 PR Analytics | Screenshot charts | App |
| 4.2.7 Issue Analytics | Screenshot charts | App |
| 4.2.8 Swagger API Docs | Screenshot /docs | App |
| 4.3 Kiểm thử | Test cases, test results | pytest output |
| 4.4 Deployment | Railway/Render deployment steps | Deployment logs |
| 4.5 Đánh giá kết quả | So sánh với yêu cầu ban đầu | Phase 1 FR/NFR table |

### Phụ lục

| Mục | Nội dung |
|---|---|
| A. Source code chính | Trích dẫn code quan trọng (models, services, routes) |
| B. Database schema | SQL CREATE TABLE statements |
| C. API Documentation | Swagger export hoặc endpoint table |
| D. Hướng dẫn cài đặt | Step-by-step setup guide |
| E. Danh sách tài liệu tham khảo | GitHub API docs, FastAPI docs, sách, bài báo |

---

## 5.7 Danh sách hình vẽ cho báo cáo

| # | Tên hình | Loại | Mục trong báo cáo |
|---|---|---|---|
| 1 | Use Case Diagram | UML | 3.2 |
| 2 | Class Diagram — Entity Models | UML | 3.3 |
| 3 | Class Diagram — Services & Repositories | UML | 3.3 |
| 4 | Sequence Diagram — Login OAuth | UML | 3.4 |
| 5 | Sequence Diagram — Sync Repository | UML | 3.4 |
| 6 | Sequence Diagram — View Dashboard | UML | 3.4 |
| 7 | Activity Diagram — Sync Process | UML | 3.5 |
| 8 | Activity Diagram — View Dashboard | UML | 3.5 |
| 9 | ERD (Entity Relationship Diagram) | Database | 3.6 |
| 10 | Architecture Overview | System | 3.8 |
| 11 | Module Boundary Diagram | System | 3.8 |
| 12 | Data Flow — Login | Flow | 3.8 |
| 13 | Data Flow — Sync | Flow | 3.8 |
| 14 | Data Flow — Dashboard | Flow | 3.8 |
| 15 | Deployment Diagram | UML | 3.9 |
| 16-25 | Screenshots giao diện | UI | 4.2 |

---

## 5.8 Danh sách bảng cho báo cáo

| # | Tên bảng | Mục |
|---|---|---|
| 1 | Functional Requirements | 3.1 |
| 2 | Non-Functional Requirements | 3.1 |
| 3 | Use Case Descriptions | 3.2 |
| 4 | Database Tables — users | 3.6 |
| 5 | Database Tables — repositories | 3.6 |
| 6 | Database Tables — contributors | 3.6 |
| 7 | Database Tables — commits | 3.6 |
| 8 | Database Tables — pull_requests | 3.6 |
| 9 | Database Tables — issues | 3.6 |
| 10 | Index Strategy | 3.6 |
| 11 | API Endpoint List | 3.7 |
| 12 | HTTP Status Codes | 3.7 |
| 13 | Error Codes | 3.7 |
| 14 | Tech Stack | 1.6 |
| 15 | Competitive Analysis | 1.1 |
| 16 | Test Cases | 4.3 |

---

## 5.9 Tài liệu tham khảo gợi ý

### Sách

1. Martin, R.C. (2017). *Clean Architecture: A Craftsman's Guide to Software Structure and Design*. Pearson.
2. Gamma, E., et al. (1994). *Design Patterns: Elements of Reusable Object-Oriented Software*. Addison-Wesley.
3. Richardson, C. (2018). *Microservices Patterns*. Manning Publications.

### Tài liệu trực tuyến

4. FastAPI Documentation. https://fastapi.tiangolo.com/
5. SQLAlchemy 2.0 Documentation. https://docs.sqlalchemy.org/
6. GitHub REST API Documentation. https://docs.github.com/en/rest
7. GitHub OAuth Apps. https://docs.github.com/en/apps/oauth-apps
8. Chart.js Documentation. https://www.chartjs.org/docs/
9. Alembic Migration Tutorial. https://alembic.sqlalchemy.org/
10. OWASP Top 10. https://owasp.org/www-project-top-ten/
11. Pydantic Documentation. https://docs.pydantic.dev/
12. Bootstrap 5 Documentation. https://getbootstrap.com/docs/5.3/

### Bài báo / Standards

13. Fielding, R.T. (2000). *Architectural Styles and the Design of Network-based Software Architectures*. Doctoral dissertation, UC Irvine.
14. RFC 6749 — The OAuth 2.0 Authorization Framework.
15. PEP 8 — Style Guide for Python Code.

---

*Kết thúc Phase 5 — UML & Report Mapping.*
*Tất cả 5 phases hoàn thành.*
