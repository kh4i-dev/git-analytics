# Công nghệ và Kiến trúc Hệ thống Git Analytics

---

## 1.1 Ngôn ngữ Python

Python là một trong những ngôn ngữ lập trình phổ biến nhất hiện nay, được sử dụng rộng rãi trong phát triển web, khoa học dữ liệu, trí tuệ nhân tạo và tự động hóa. Với cú pháp đơn giản, dễ đọc và hệ sinh thái thư viện phong phú, Python là lựa chọn hàng đầu cho các dự án analytics và backend.

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
graph LR
    subgraph Python["Hệ sinh thái Python"]
        A["Python 3.11+"]
        B["Web Frameworks<br>FastAPI, Flask, Django"]
        C["ORM<br>SQLAlchemy 2.0"]
        D["HTTP Client<br>httpx"]
        E["Template<br>Jinja2"]
        F["Auth<br>OAuth, JWT"]
    end
    A --> B
    A --> C
    A --> D
    A --> E
    A --> F
```

</div>

*Hình 1.1: Hệ sinh thái ngôn ngữ lập trình Python trong Git Analytics*

---

Python còn hỗ trợ nhiều framework hiện đại như Flask, Django và FastAPI. Trong dự án Git Analytics, FastAPI được chọn làm framework chính nhờ hiệu suất async vượt trội, tự động sinh tài liệu Swagger, và hỗ trợ type hints với Pydantic.

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
graph TB
    subgraph Frameworks["Hệ sinh thái Framework Python"]
        FastAPI["FastAPI<br>Async, Swagger, Pydantic"]
        Flask["Flask<br>Đơn giản, linh hoạt"]
        Django["Django<br>All-in-one, batteries included"]
    end

    subgraph GitAnalytics["Git Analytics sử dụng"]
        Selected["FastAPI"]
        Reason1["Async HTTP với httpx"]
        Reason2["Tự động Swagger UI"]
        Reason3["Type-safe với Pydantic"]
        Reason4["Hiệu suất cao (Starlette)"]
    end

    Frameworks --> Selected
    Selected --> Reason1
    Selected --> Reason2
    Selected --> Reason3
    Selected --> Reason4
```

</div>

*Hình 1.2: Một số framework phổ biến trong hệ sinh thái Python và lý do chọn FastAPI*

---

## 1.2 OOP (Lập trình hướng đối tượng)

Lập trình hướng đối tượng (OOP) là mô hình lập trình dựa trên khái niệm lớp (Class) và đối tượng (Object). OOP giúp tổ chức code theo hướng module, dễ bảo trì và mở rộng. Git Analytics áp dụng OOP trong toàn bộ kiến trúc.

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
classDiagram
    class Class {
        +Thuộc tính (Attributes)
        +Phương thức (Methods)
    }
    class Object1["Object 1"] {
        +value = "instance 1"
    }
    class Object2["Object 2"] {
        +value = "instance 2"
    }
    class Object3["Object 3"] {
        +value = "instance 3"
    }

    Class --> Object1 : instantiate
    Class --> Object2 : instantiate
    Class --> Object3 : instantiate
```

</div>

*Hình 1.3: Mô hình lập trình hướng đối tượng — Class và Object*

---

Ví dụ về tính kế thừa (Inheritance) trong Git Analytics:

- **BaseAIProvider** — lớp cơ sở định nghĩa interface chung
- **GeminiProvider** — kế thừa và implement cho Google Gemini
- **OpenAIProvider** — kế thừa và implement cho OpenAI

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
classDiagram
    class BaseAIProvider {
        +generate(prompt: str) str
        +validate_response() bool
    }
    class GeminiProvider {
        +generate(prompt: str) str
        +validate_response() bool
    }
    class OpenAIProvider {
        +generate(prompt: str) str
        +validate_response() bool
    }
    class LocalProvider {
        +generate(prompt: str) str
        +validate_response() bool
    }

    BaseAIProvider <|-- GeminiProvider : extends
    BaseAIProvider <|-- OpenAIProvider : extends
    BaseAIProvider <|-- LocalProvider : extends
```

</div>

*Hình 1.4: Mô hình kế thừa giữa các AI Provider*

---

## 1.3 Công nghệ Web & Framework

FastAPI là framework web hiện đại dành cho Python, được xây dựng trên Starlette và Pydantic. FastAPI hỗ trợ async/await, tự động validation request/response, và sinh tài liệu OpenAPI (Swagger) tự động.

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
graph TB
    Request["HTTP Request"] --> FastAPIApp["FastAPI Application"]

    subgraph FastAPIApp
        Router["Router Layer<br>/api/v1/* /dashboard/*"]
        Middleware["Middleware<br>Auth, CORS, Logging"]
        Dependencies["Dependencies<br>DI, Session, User"]
    end

    Router --> Service["Service Layer"]
    Service --> ORM["SQLAlchemy ORM"]
    Service --> Client["GitHub Client"]
    ORM --> DB["PostgreSQL / SQLite"]
    Client --> GitHub["GitHub REST API"]

    FastAPIApp --> Response["JSON / HTML Response"]
    FastAPIApp --> Swagger["Swagger UI<br>/docs"]
```

</div>

*Hình 1.5: Kiến trúc hoạt động của FastAPI Framework*

---

Frontend của hệ thống được xây dựng bằng HTML5, CSS3 và JavaScript thuần với kiến trúc hybrid routing: server-render pages kết hợp async JSON API.

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
graph TB
    User["User / Developer"]

    subgraph Frontend["Frontend Layer"]
        Pages["Jinja2 Templates<br>Server-rendered Pages"]
        Charts["Chart.js<br>Interactive Charts"]
        UI["Dark SaaS UI<br>GitHub / Vercel Inspired"]
    end

    subgraph Backend["Backend Layer"]
        Routes["FastAPI Routes<br>/dashboard/* /api/v1/* /auth/* /reports/*"]
        Services["Services<br>Sync, Analytics, Reports, AI, Export"]
        Clients["GitHub REST API Client<br>httpx, Pagination, Rate Limiting"]
    end

    subgraph Data["Data Layer"]
        ORM_Layer["SQLAlchemy 2.0 + Alembic"]
        DB_Server["PostgreSQL / SQLite"]
    end

    User --> Frontend
    Frontend -- page routes --> Routes
    Frontend -- fetch /api/v1/* --> Routes
    Routes --> Services
    Services --> Clients
    Services --> ORM_Layer
    Clients --> GitHub_API["GitHub API<br>api.github.com"]
    ORM_Layer --> DB_Server
```

</div>

*Hình 1.6: Kiến trúc tổng quan hệ thống Git Analytics*

---

## 1.4 Database

Hệ thống sử dụng SQLAlchemy ORM để tương tác với cơ sở dữ liệu. SQLAlchemy cung cấp abstraction layer giúp chuyển đổi giữa Python objects và database tables, hỗ trợ cả SQLite (phát triển) và PostgreSQL (sản xuất). Alembic quản lý migrations schema.

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
graph LR
    subgraph App["Python Application"]
        Models["SQLAlchemy Models<br>User, Repository, Commit<br>PullRequest, Issue, Report"]
    end

    subgraph ORM["SQLAlchemy ORM"]
        Session["Session<br>Unit of Work"]
        Query["Query Builder<br>SQL Aggregation"]
        Mapping["ORM Mapping<br>Table -> Python Object"]
    end

    subgraph Migrations["Alembic Migrations"]
        Migrate["upgrade / downgrade"]
        AutoGen["auto-generate<br>revision"]
    end

    subgraph Database["Database"]
        SQLite["SQLite (dev)<br>git_analytics.db"]
        PostgreSQL["PostgreSQL (prod)"]
    end

    Models --> Session
    Session --> Mapping
    Mapping --> Query
    Query --> Database
    Migrations --> Database
    AutoGen --> Migrate
```

</div>

*Hình 1.7: Quy trình tương tác giữa SQLAlchemy và PostgreSQL*

---

## 1.5 API & GitHub API

API là phương thức cho phép các hệ thống giao tiếp với nhau thông qua các endpoint được định nghĩa trước. Git Analytics sử dụng kiến trúc RESTful API với định dạng JSON chuẩn cho tất cả response.

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
sequenceDiagram
    participant Client as Client (Browser)
    participant API as FastAPI Routes
    participant Service as Service Layer
    participant DB as Database

    Client->>API: GET /api/v1/repositories
    API->>Service: get_user_repos()
    Service->>DB: SELECT repositories
    DB-->>Service: repo list
    Service-->>API: Repository list
    API-->>Client: { data: [...], meta: { ... } }

    Client->>API: GET /api/v1/analytics/{repo_id}/commits
    API->>Service: get_commit_metrics(repo_id)
    Service->>DB: SELECT COUNT, DATE(created_at)
    Service->>DB: GROUP BY date
    DB-->>Service: Aggregated results
    Service-->>API: Commit stats
    API-->>Client: { data: { commits_by_date: [...] }, meta: { ... } }

    Note over Client,DB: Response: { data, error, meta }
```

</div>

*Hình 1.8: Mô hình giao tiếp RESTful API*

---

GitHub REST API được sử dụng để lấy thông tin repository, commits, pull requests và issues. Git Analytics sử dụng GitHubClient adapter để xử lý authentication, pagination (per_page=100) và rate limiting.

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
sequenceDiagram
    participant Sys as Git Analytics
    participant GitHub as GitHub REST API
    participant DB as Database

    Note over Sys,DB: Pre-sync check
    Sys->>GitHub: GET /rate_limit
    GitHub-->>Sys: { remaining: 4500 }

    Note over Sys,DB: Full sync (first time)
    Sys->>GitHub: GET /repos/{owner}/{repo}/commits?per_page=100
    GitHub-->>Sys: page 1 (Link header: next)
    Sys->>GitHub: GET /repos/{owner}/{repo}/commits?page=2
    GitHub-->>Sys: page 2 (Link header: next)
    Sys->>GitHub: GET /repos/{owner}/{repo}/commits?page=3
    GitHub-->>Sys: page 3 (no next -> done)

    Sys->>GitHub: GET /repos/{owner}/{repo}/pulls?state=all&per_page=100
    GitHub-->>Sys: all pull requests

    Sys->>GitHub: GET /repos/{owner}/{repo}/issues?state=all&per_page=100
    GitHub-->>Sys: all issues

    Note over Sys,DB: Persist data
    Sys->>DB: Upsert commits (unique: sha)
    Sys->>DB: Upsert PRs (unique: number)
    Sys->>DB: Upsert issues (unique: number)
    Sys->>DB: Update last_synced_at
    Sys->>DB: Set status = success

    Note over Sys,DB: Incremental sync (next time)
    Sys->>GitHub: GET /commits?since=2024-01-01T00:00:00Z
    GitHub-->>Sys: only new commits
```

</div>

*Hình 1.9: Quy trình đồng bộ dữ liệu từ GitHub API*
