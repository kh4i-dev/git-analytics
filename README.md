# Git Analytics

<p align="center">
  <a href="https://github.com/kh4i-dev/git-analytics/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python"></a>
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/fastapi-latest-009688.svg" alt="FastAPI"></a>
  <a href="https://github.com/kh4i-dev/git-analytics"><img src="https://img.shields.io/badge/architecture-layered-blueviolet.svg" alt="Architecture"></a>
  <a href="https://github.com/kh4i-dev/git-analytics"><img src="https://img.shields.io/badge/AI--workspace-dual--mode-orange.svg" alt="AI Workspace"></a>
</p>

An enterprise-ready, self-hosted Engineering Intelligence Platform that integrates with GitHub OAuth. It synchronizes source code metadata to provide engineering-grade metrics, dynamic branch-aware dashboard analytics, immutable sharing-enabled reports, and an AI-driven workspace for developers and engineering leaders.

---

## 📌 Project Overview

**Git Analytics** bridges the gap between raw git histories and actionable engineering insights. By securely connecting to a GitHub account using OAuth, it runs highly efficient background sync workers to populate a local analytics engine. 

### Why Git Analytics?
* **For Engineering Managers & Tech Leads**: Gain absolute visibility into development velocity, contribution patterns, and pull request lifecycles without high-cost SaaS subscription fees. Generate immutable periodic snapshots to share with stakeholders securely.
* **For Software Engineers**: Boost productivity using a specialized AI Workspace. Automatically generate standard Conventional Commit messages from raw code diffs, run secure in-context security and performance reviews on PR diffs, and query a Repository AI Assistant about system architectures in natural language.

---

## 🖼️ Preview & Screenshots Gallery

Explore the interactive interfaces, diagnostic dashboards, and reporting modules of Git Analytics:

### 1. User Authentication & Onboarding
<p align="center">
  <img width="900" src="./images/login_page.png" alt="User Login Screen" />
  <br>
  <em>Figure 1: Secure Login Portal with GitHub OAuth Authorization</em>
</p>

### 2. Multi-Repository Management & Synchronizing Status
<p align="center">
  <img width="900" src="./images/repositories_sync_dashboard.png" alt="Repositories Sync Dashboard" />
  <br>
  <em>Figure 2: Repository Synchronization Hub showcasing real-time progress, commit counts, and branch statuses</em>
</p>

### 3. Engineering Intelligence Analytics Dashboard
<p align="center">
  <img width="900" src="./images/dashboard_overview.png" alt="Dashboard Overview" />
  <br>
  <em>Figure 3: High-Level Analytics Dashboard with contribution streaks, activity heatmaps, and repository velocity metrics</em>
</p>

### 4. Single Repository Insights
<p align="center">
  <img width="900" src="./images/repository_details_overview.png" alt="Repository Details Overview" />
  <br>
  <em>Figure 4: Detailed metrics of a single repository filtered by specific branches, highlighting PR velocities and issue statistics</em>
</p>

### 5. Deep-Dive Commit Analytics
<p align="center">
  <img width="900" src="./images/single_commit_analysis.png" alt="Single Commit Analysis" />
  <br>
  <em>Figure 5: Granular single-commit code change analysis, streak metrics, and workload distributions</em>
</p>

### 6. Decoupled AI Assistant Workspace
<p align="center">
  <img width="900" src="./images/ai_assistant_workspace.png" alt="AI Assistant Workspace" />
  <br>
  <em>Figure 6: Contextual AI Workspace for natural language repository querying, security reviews, and Conventional Commit generation</em>
</p>

### 7. Interactive API Documentation & Payload
<p align="center">
  <img width="900" src="./images/swagger_api_docs.png" alt="Swagger API Docs" />
  <br>
  <em>Figure 7: Interactive OpenAPI Swagger UI documentation for all platform endpoint routes</em>
</p>

<p align="center">
  <img width="600" src="./images/api_json_payload.png" alt="API JSON Payload" />
  <br>
  <em>Figure 8: Clean, structured JSON response payloads served by the FastAPI analytics engine</em>
</p>

### 8. Immutable PDF Executive Reports
<p align="center">
  <img width="450" src="./images/pdf_report_page_1.png" alt="PDF Report Page 1" />
  <img width="450" src="./images/pdf_report_page_2.png" alt="PDF Report Page 2" />
  <br>
  <em>Figure 9: High-fidelity exported PDF Engineering Executive Reports with streaks, commit summaries, and repository heatmaps</em>
</p>

### 9. System Use Case Diagram
<p align="center">
  <img width="700" src="./images/use_case_diagram.png" alt="System Use Case Diagram" />
  <br>
  <em>Figure 10: System boundaries, actor scopes, and functional use cases diagram</em>
</p>

### 10. Repository Synchronizer Architecture Diagrams
<p align="center">
  <img width="850" src="./docs/diagrams/activity_diagram_sync_repository.svg" alt="Incremental Repository Sync Flow" />
  <br>
  <em>Figure 11: High-Level Incremental Repository Synchronization Activity Diagram</em>
</p>

<p align="center">
  <img width="850" src="./docs/diagrams/activity_diagram_fetch_pagination.svg" alt="Paginated GitHub Fetch Flow" />
  <br>
  <em>Figure 12: Paginated GitHub API Metadata Retrieval Activity Diagram</em>
</p>

---

## 🚀 Key Features

* **Incremental GitHub Synchronization**: Smart asynchronous data ingestion that maps commits, branches, pull requests, issues, and contributors, respecting GitHub's rate-limits and utilizing conditional caching.
* **Dynamic Branch-Aware Analytics**: Selectively filter all metrics, charts, and activity heatmaps globally by branch, enabling deep-dive analysis of feature branches vs. production.
* **Immutable Engineering Reports**: Capture the repository's analytical state at any given second into a frozen snapshot. Automatically draft release notes, detailed changelogs, and risk assessments.
* **Anonymous Share Links (Capability URLs)**: Securely publish reports to external users via randomly-generated secure share tokens. Revoke access instantly, with names and emails anonymized to guarantee data privacy.
* **Dual-Mode AI Workspace**: A robust, decoupled AI execution system supporting:
  * **BYOK (Bring Your Own Key)**: Personal API keys stored with AES-256 Fernet symmetric cryptography in the database.
  * **Cloud AI**: Server-managed key integrations routing through configured providers or standard OpenAI-compatible gateways.
* **AI Commit & Code Review**: Streamlined workspace to draft Conventional Commit messages from git diff inputs and execute deep security, logic, and test-coverage reviews.

---

## 📐 System Architecture

Git Analytics utilizes a clean **Layered Architecture (3-layer)** combined with **Hybrid Routing** (server-rendered interactive dashboards via Jinja2 + dynamic JSON APIs for background updates).

### System Component Boundaries
* **Client Presentation Layer**: Compiled server-side Jinja2 templates styled with a premium Dark SaaS theme. Dynamic data binding is handled with standard Chart.js for real-time visualization and Tailwind-inspired custom typography.
* **FastAPI Server (Routing & Auth)**: Handles API endpoints, signed HTTP-only cookie-session parsers, and custom exception-mapping middlewares.
* **Service Business Layer**: Pure OOP service modules executing core algorithms (Streaks calculations, Health Scoring, Symmetric Encryption, AI Prompts construction, and immutable PDF/Excel generation).
* **Repository Data Layer**: Clean SQLAlchemy 2.0 interface mappings implementing decoupled Data Access Objects (DAOs) for database operations.
* **Background Queue**: Safe, thread-safe Python standard worker thread executing asynchronous repository synchronization tasks out-of-band.

---

## 📊 Tech Stack

| Layer | Technologies | Primary Responsibility |
|---|---|---|
| **Frontend UI** | HTML5, Jinja2, Vanilla CSS | Server-side HTML render, sleek Dark SaaS aesthetic styling, responsive layouts |
| **Data Viz** | Chart.js, HTML Canvas | Paint interactive velocity charts, contribution heatmaps, and distribution graphs |
| **API Backend** | FastAPI, Python 3.11+ | High-performance HTTP routing, Dependency Injection, request validation, middleware |
| **Background Jobs** | Standard Threading, Queue | Thread-safe, non-blocking queue worker executing paginated sync scripts asynchronously |
| **Cryptography** | Cryptography (Fernet) | Symmetric encryption of user-supplied BYOK API keys using a server secret |
| **ORM / Migration** | SQLAlchemy 2.0, Alembic | Database entity mapping, declarative sessions, linear migration tracking |
| **Database** | SQLite (Dev) / PostgreSQL (Prod) | Durable structured storage for aggregated git entities |
| **HTTP Client** | HTTPX | Asynchronous, connection-pooled client querying external GitHub and LLM endpoints |

---

## 📂 Project Structure

```text
git-analytics/
├── alembic.ini                   # Database migration engine configuration
├── requirements.txt               # Pinpoint pip library dependencies
├── app/                          # Core codebase directory
│   ├── main.py                   # FastAPI application factory & routers registration
│   ├── clients/                  # Third-party API wrappers (GitHub, AI services)
│   ├── core/                     # Application configurations, logging, exceptions, and security
│   ├── db/                       # SQLAlchemy engine creation & base models declarations
│   ├── models/                   # SQLAlchemy database tables mappings (declarative models)
│   ├── pdf_export/               # Binary PDF & Excel serialization services
│   ├── repositories/             # Data access objects (DAOs) encapsulating raw SQL queries
│   ├── routes/                   # FastAPI route controllers (Auth, API, UI views)
│   ├── schemas/                  # Typed Pydantic data models for input validation
│   ├── services/                 # Business logic engines (Sync, Analytics, AI, Reports)
│   └── utils/                    # Common helper modules
├── docs/                         # In-depth technical documentation suite
│   ├── CONTEXT.md                # Domain terminology and project glossary
│   ├── PLAN.md                   # Phased web improvement plans
│   ├── ai/                       # AI Workspace architecture and guides
│   ├── analytics/                # Mathematical calculation formulas
│   ├── architecture/             # Structural designs and ADR (Architectural Decision Records)
│   ├── reports/                  # Engineering reports system designs
│   ├── roadmap/                  # Version changelogs and evolutionary phases
│   └── setup/                    # Local installation & visual UI styling guides
├── static/                       # Client-side static resources (CSS, JS)
├── templates/                    # Server-side Jinja2 components & layout files
└── tests/                        # Comprehensive test cases suite (pytest)
```

---

## 📈 Analytics & KPI Formulas

The platform utilizes custom-developed formulas to measure repository health and contributor impact:

### 1. Repository Health Score ($H_R$)
Combines active contributions, issue resolution rate, and PR merge velocity:
$$H_R = (w_c \times C_s) + (w_i \times I_r) + (w_p \times P_v)$$
Where:
* $C_s$ (Commit Score): Logarithmic scaling of commit volume in the past 30 days.
* $I_r$ (Issue Resolution Ratio): Resolved issues / Total issues created in the period.
* $P_v$ (PR Velocity Score): Average hours from PR creation to merge, inversely scaled.
* $w_c, w_i, w_p$: Weight constants (default: 0.4, 0.3, 0.3).

### 2. Contribution Streak
Calculated using a modified sliding-window algorithm that tracks consecutive active days, allowing for a configurable "weekend grace period" to measure sustainable engineering momentum.

---

## 🤖 AI Workspace & Retrieval Flow

The AI assistant operates within strict, secure logical boundaries.

* **Secret Locality Invariant**: API keys entered in BYOK mode are decrypted solely inside the memory boundary of the active execution request. They are never written to server logs, stdout, browser local storage, or temporary files.
* **Context Aggregation (RAG)**: The assistant queries local synchronized DB entities (commit structures, file hierarchies, metadata) and stitches them into custom XML schemas inside the system prompts, ensuring the LLM has complete context without violating token boundaries.

---

## 📐 Architecture Diagrams

The 10 structural blueprints below reflect the real production implementation of Git Analytics:

### 1. High-Level System Architecture
```mermaid
flowchart TB
    subgraph Client ["Browser Client Layer"]
        UI["Jinja2 Templates"]
        Charts["Chart.js Analytics"]
        Static["TailwindCSS / Vanilla CSS"]
    end

    subgraph FastAPI ["FastAPI Application (Stateless Backend)"]
        direction TB
        Routes["Routing Layer<br>(HTML Pages & JSON APIs)"]
        AuthMid["Auth Middleware / Dependencies"]
        Services["Service Layer<br>(Business & Aggregation Logic)"]
        SyncQ["Sync Job Queue<br>(In-Memory Background Worker)"]
        Repos["Repository Layer<br>(Data Access Objects)"]
        DBEngine["SQLAlchemy 2.0 ORM<br>(Engine & Session Management)"]
    end

    subgraph External ["External Services"]
        GitHub["GitHub REST API<br>(Incremental OAuth Sync)"]
        AILayer["AI Providers<br>(Gemini, OpenAI, Claude, OpenClaw)"]
    end

    subgraph Storage ["Persistent Storage"]
        DB[("SQLite Database (Dev)<br>/ PostgreSQL (Prod)")]
    end

    UI --> Routes
    Routes --> AuthMid
    AuthMid --> Services
    Services --> Repos
    Services --> SyncQ
    SyncQ --> GitHub
    Services --> AILayer
    Repos --> DBEngine
    DBEngine --> DB
    
    classDef client fill:#e3f2fd,stroke:#0d47a1,stroke-width:2px;
    classDef fastapi fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;
    classDef external fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef db fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    
    class Client,UI,Charts,Static client;
    class FastAPI,Routes,AuthMid,Services,SyncQ,Repos,DBEngine fastapi;
    class External,GitHub,AILayer external;
    class Storage,DB db;
```

### 2. Authentication Flow (GitHub OAuth)
```mermaid
sequenceDiagram
    autonumber
    actor User as Engineer / User
    participant Browser as Web Browser
    participant API as FastAPI Server
    participant DB as SQLite / PostgreSQL
    participant GitHub as GitHub OAuth / API

    User->>Browser: Click "Login with GitHub"
    Browser->>API: GET /auth/github/login
    API-->>Browser: Redirect to GitHub OAuth consent screen
    Browser->>GitHub: Request Auth with Client ID & Scope (repo, user:email)
    GitHub-->>User: Present authorization prompt
    User->>GitHub: Approve authorization scopes
    GitHub-->>Browser: Redirect to redirect_uri with temporary code
    Browser->>API: GET /auth/github/callback?code=TEMP_CODE
    API->>GitHub: POST /login/oauth/access_token (code, client_id, secret)
    GitHub-->>API: Return access_token
    API->>API: Encrypt token with Fernet using server ENCRYPTION_KEY
    API->>DB: Upsert User record (github_id, username, encrypted_token)
    DB-->>API: User persisted
    API->>API: Generate HTTP-Only, Secure, Signed Session Cookie (user_id)
    API-->>Browser: Set Session Cookie & Redirect to /dashboard
    Browser-->>User: Render authenticated Dashboard View
```

### 3. Analytics Processing Flow
```mermaid
flowchart TD
    subgraph Browser ["Client Presentation"]
        UI["Render Page Skeleton"]
        Fetch["Async Fetch: /api/v1/analytics/*"]
        Draw["Chart.js Render Visualizations"]
    end

    subgraph Service ["Business Aggregation Layer"]
        Router["FastAPI Endpoint Router"]
        AnalyticsService["AnalyticsService Engine"]
    end

    subgraph Persistence ["SQLAlchemy Data Access"]
        CommitRepo["Commit Repository Queries"]
        PRRepo["Pull Request Queries"]
        IssueRepo["Issue Queries"]
        DB[("Database Engine")]
    end

    UI --> Fetch
    Fetch --> Router
    Router --> AnalyticsService
    AnalyticsService --> CommitRepo & PRRepo & IssueRepo
    CommitRepo & PRRepo & IssueRepo --> DB
    DB -->|Raw SQL Aggregations| AnalyticsService
    AnalyticsService -->|Compute Streak & Health Scores| Router
    Router -->|"JSON Shape: { data, error, meta }"| Fetch
    Fetch --> Draw
```

### 4. Repository Sync Flow (Incremental Pagination)
```mermaid
flowchart TD
    Start([User Triggers Sync]) --> Auth{Validate Cookie & Repo ID}
    Auth -->|Valid| Queue[Push to Background Sync Queue]
    Auth -->|Invalid| Err[401 / 403 HTTP Error]
    Queue --> Worker[Worker Thread Dequeues SyncJob]
    
    subgraph JobProcessing ["Asynchronous Job Execution"]
        Worker --> CheckRate{Verify GitHub Rate Limit}
        CheckRate -->|Sufficient| SyncCommits[Sync Default Branch Commits]
        CheckRate -->|Exhausted| Backoff[Wait / Pause Sync Job]
        
        SyncCommits --> Incremental{Latest SHA matches DB?}
        Incremental -->|No| FetchPage[Fetch Commits Page from GitHub]
        Incremental -->|Yes| SyncPRs[Sync Pull Requests]
        
        FetchPage --> SaveCommits[Upsert Commits Batch to DB] --> FetchPage
        SyncPRs --> SavePRs[Upsert Pull Requests to DB]
        SavePRs --> SyncIssues[Sync Issues]
        SyncIssues --> SaveIssues[Upsert Issues to DB]
        
        SaveIssues --> Complete[Update last_sync_status = 'success', status = 'active']
        
        %% Exception handling
        CheckRate -.->|404 Not Found| MarkUnavailable[Update last_sync_status = 'failed', status = 'unavailable']
        SyncCommits -.->|Error| Fail[Update last_sync_status = 'failed', last_sync_error = 'Error Msg']
    end
    
    Complete & Fail & MarkUnavailable --> End([End Job])
```

### 5. Database Relationship Diagram (ERD)
```mermaid
erDiagram
    users {
        int id PK
        string github_id UK
        string username
        string email
        string encrypted_github_token
        datetime created_at
        datetime updated_at
    }
    repositories {
        int id PK
        string github_id UK
        string name
        string owner
        string default_branch
        datetime last_synced_at
        string last_sync_status
        string status
        string last_sync_error
        int user_id FK
    }
    branches {
        int id PK
        string name
        boolean is_default
        string last_commit_sha
        int repository_id FK
    }
    commits {
        int id PK
        string sha UK
        string message
        string author_name
        string author_email
        datetime date
        int additions
        int deletions
        int repository_id FK
        int branch_id FK
    }
    pull_requests {
        int id PK
        string github_id UK
        int number
        string title
        string state
        boolean is_merged
        datetime merged_at
        datetime created_at
        datetime closed_at
        int additions
        int deletions
        int repository_id FK
        int user_id FK
    }
    issues {
        int id PK
        string github_id UK
        int number
        string title
        string state
        datetime created_at
        datetime closed_at
        json labels
        int repository_id FK
    }
    contributors {
        int id PK
        string github_login UK
        string avatar_url
        string email
        int repository_id FK
    }
    engineering_reports {
        int id PK
        string title
        datetime range_start
        datetime range_end
        boolean is_immutable
        string share_token UK
        json snapshot_data
        int repository_id FK
    }
    ai_provider_settings {
        int id PK
        int user_id FK
        string provider_name
        string encrypted_api_key
        string api_base_url
        boolean is_active
    }
    ai_usage_events {
        int id PK
        int user_id FK
        string provider
        string operation
        int token_count
        datetime created_at
    }

    users ||--o{ repositories : "manages"
    users ||--o{ ai_provider_settings : "configures"
    users ||--o{ ai_usage_events : "incurs"
    repositories ||--o{ branches : "contains"
    repositories ||--o{ commits : "tracks"
    repositories ||--o{ pull_requests : "receives"
    repositories ||--o{ issues : "manages"
    repositories ||--o{ contributors : "gathers"
    repositories ||--o{ engineering_reports : "generates"
    branches ||--o{ commits : "contains"
```

### 6. AI Assistant Workflow
```mermaid
flowchart TD
    subgraph UI ["User Interface"]
        Input["User Request (Diff, PR, or natural question)"]
        Badge["AI Status Badge: BYOK or Cloud AI"]
    end

    subgraph Service ["AI Operations Processor"]
        Router["POST /api/v1/ai/query"]
        ConfigCheck{"Check AI Configuration"}
        BYOKDec["Decrypt symmetric BYOK key"]
        CloudDec["Fetch server-side Cloud API key"]
        ContextAssembler["Context & Prompts Assembler"]
        
        subgraph Templates ["Jinja System Prompts"]
            CommitPrompt["Conventional Commit System Prompt"]
            ReviewPrompt["PR Security & Performance System Prompt"]
            RAGPrompt["Repository Semantic Context RAG Prompt"]
        end
    end

    subgraph External ["LLM Endpoint"]
        APIClient["HTTPX Async Call"]
        LLM["Gemini / OpenAI / Anthropic"]
    end

    Input --> Router
    Router --> ConfigCheck
    ConfigCheck -->|BYOK Mode| BYOKDec
    ConfigCheck -->|Cloud Mode| CloudDec
    
    BYOKDec & CloudDec --> ContextAssembler
    
    %% Context sources
    DB[("SQLite DB (Metadata context)")] --> ContextAssembler
    GitDiff["Git Diff Input"] --> ContextAssembler
    
    ContextAssembler --> Templates
    Templates --> APIClient
    APIClient --> LLM
    LLM -->|Stream / Return JSON or Markdown| Router
    Router --> LogUsage[Insert record to ai_usage_events]
    Router -->|JSON Output| UI
```

### 7. API Request Lifecycle
```mermaid
sequenceDiagram
    autonumber
    participant Browser as Web Browser Client
    participant TraceMid as Trace ID Middleware
    participant AuthDep as Session Auth Dependency
    participant Router as API Router Controller
    participant Service as Domain Service Layer
    participant ExMid as Exception Handler Middleware

    Browser->>TraceMid: HTTP Request (Optional x-trace-id header)
    alt x-trace-id Header present
        TraceMid->>TraceMid: Store trace ID in contextvars
    else Header absent
        TraceMid->>TraceMid: Generate UUIDv4, store in contextvars
    end
    TraceMid->>AuthDep: Forward HTTP Request
    AuthDep->>AuthDep: Parse & Decrypt Cookie Session
    alt Session Valid
        AuthDep->>Router: Inject Current User Object
        Router->>Service: Execute Domain Handler logic
        alt Domain Handler Success
            Service-->>Router: Domain Return Value
            Router-->>TraceMid: JSON response { data: data, error: null }
        else Domain Exception Raised (e.g., RepoNotFound)
            Service-->>ExMid: Raise DomainException
            ExMid->>ExMid: Format JSON standard error response
            ExMid-->>TraceMid: HTTP 404 JSON { data: null, error: { message, code } }
        end
    else Session Invalid / Expired
        AuthDep-->>ExMid: Raise CredentialsException
        ExMid-->>TraceMid: HTTP 401 JSON { data: null, error: { message: "Unauthorized" } }
    end
    TraceMid-->>Browser: HTTP Response (Contains x-trace-id Header)
```

### 8. Deployment Architecture
```mermaid
flowchart TD
    User([User Traffic]) --> DNS[Cloudflare DNS & WAF]
    DNS -->|HTTPS Port 443| RevProxy[Nginx Reverse Proxy & SSL Termination]
    
    subgraph ServerNode ["SaaS Application Host Node"]
        RevProxy -->|Internal Route Port 8000| Uvicorn[Uvicorn ASGI Server]
        
        subgraph FastAPIInstances ["FastAPI Scaling Groups"]
            Uvicorn --> CoreApp[FastAPI Application Instances]
            CoreApp --> StaticMount[Static Files Middleware]
            CoreApp --> RouterLayer[Router Layers]
        end
        
        RouterLayer --> MemoryQ["In-Memory SyncQueue<br>(Background Threads)"]
    end

    CoreApp -->|Symmetric Encryption / Decryption| Fernet[Fernet Crypto Modules]
    
    subgraph DataTier ["Secure Persistence Layer"]
        RouterLayer & MemoryQ --> PostgreSQL[(Production PostgreSQL DB)]
    end

    subgraph OuterWorld ["External Integrations"]
        MemoryQ -->|Outbound HTTPS| GitHubAPI[GitHub REST API]
        RouterLayer -->|Outbound HTTPS| AIServices[Gemini, OpenAI, Anthropic APIs]
    end
```

### 9. Background Job / Queue Flow
```mermaid
sequenceDiagram
    autonumber
    participant Browser as Web Browser Client
    participant Router as Sync Router Endpoint
    participant Queue as In-Memory Queue (sync_queue)
    participant Worker as Background Worker Thread
    participant GitHub as GitHub API
    participant DB as SQLite / PostgreSQL

    Browser->>Router: POST /api/v1/sync (repo_id)
    Router->>DB: Create / Update SyncJob record (status='pending')
    Router->>Queue: Push repo_id task to Python Queue
    Router-->>Browser: HTTP 202 Accepted (Sync started in background)
    
    Note over Worker,Queue: Continuous worker loop polling
    Worker->>Queue: Get task (repo_id)
    Queue-->>Worker: Return repo_id
    Worker->>DB: Update SyncJob status='running'
    
    loop Incremental Page Syncing
        Worker->>GitHub: GET Page of Commits / PRs / Issues
        GitHub-->>Worker: Return API objects
        Worker->>DB: Upsert batch items (commits, PRs, issues)
    end
    
    alt Sync Successful
        Worker->>DB: Update SyncJob status='success', last_synced_at=now()
    else Sync Fails / rate-limit / 404
        Worker->>DB: Update SyncJob status='failed', last_sync_error='Error details'
    end
    
    Browser->>Router: GET /api/v1/sync/status (repo_id)
    Router->>DB: Fetch latest SyncJob details
    DB-->>Router: Status details
    Router-->>Browser: JSON response (e.g. status='success')
```

### 10. User Permission Flow
```mermaid
flowchart TD
    subgraph UserRoles ["User Roles / Authentication State"]
        Anon[Anonymous / Public Visitor]
        User[Authenticated User]
    end

    subgraph Pages ["System Target Resources"]
        Landing["Landing Page (/)"]
        ShareLink["Public Share Link (/reports/share/{token})"]
        Dashboard["Private Dashboard (/dashboard)"]
        SyncAPI["Sync Trigger (/api/v1/sync)"]
        AISpace["AI Workspace (/api/v1/ai)"]
    end

    subgraph Guards ["Authorization Rules Gate"]
        OAuthGuard{Check signed cookie user_id}
        RepoGuard{Does repo belong to user?}
        ReportGuard{Does token match database?}
    end

    Anon --> Landing
    Anon --> ShareLink --> ReportGuard
    ReportGuard -->|Valid Token| R_Report[Serve Read-Only Immutable Report]
    ReportGuard -->|Invalid Token| R_404[HTTP 404 Not Found]

    User --> Dashboard & SyncAPI & AISpace --> OAuthGuard
    
    OAuthGuard -->|No Cookie / Invalid| R_401[HTTP 401 Unauthorized Redirect]
    OAuthGuard -->|Valid Cookie| RepoGuard
    
    RepoGuard -->|"Yes (user_id matches repo.user_id)"| Access[Grant Access to Private Resource]
    RepoGuard -->|"No (Resource cross-ownership violation)"| R_403[HTTP 403 Forbidden]
```

---

## 🔒 Security Considerations

* **Symmetric Database Encryption**: User-supplied API keys for Gemini, Claude, or OpenAI are encrypted server-side with AES-256 Fernet (using python's `cryptography` library) driven by the unique `ENCRYPTION_KEY` env var.
* **HTTP-Only Cookies**: User sessions are saved in tamper-proof, signed HTTP-only cookies to prevent client-side script inspection (XSS vector prevention).
* **OAuth Scope Minimization**: The platform requests standard GitHub scopes (`repo` for reading private repos metadata) and operates purely on read-only business paths.

---

## ⚡ Performance Optimization

* **Conditional Sync Checkpoints**: Synced repository commits check the latest hash locally to execute immediate early-exits for up-to-date repositories, saving API quota.
* **Aggregated Indexes**: Added composite indexes on commits database: `(repository_id, date)` and `(repository_id, author_email)` to render Chart.js aggregates in sub-millisecond durations.

---

## 💻 Installation & Setup

### Prerequisites
* **Python 3.11 or higher**
* **GitHub developer account** (to create an OAuth application)

### 1. Retrieve the Repository
```bash
git clone https://github.com/kh4i-dev/git-analytics.git
cd git-analytics
```

### 2. Configure Environment Variables
Copy the sample environment configuration:
```bash
# On Windows:
copy .env.example .env
# On macOS / Linux:
cp .env.example .env
```
Open `.env` and fill out the GitHub Client credentials:
```env
# Server settings
APP_NAME="Git Analytics Platform"
DEBUG=True
SECRET_KEY="generate-a-long-random-string-for-session-signing"
ENCRYPTION_KEY="generate-a-32-byte-base64-fernet-key"

# GitHub OAuth credentials
GITHUB_CLIENT_ID="your_oauth_client_id"
GITHUB_CLIENT_SECRET="your_oauth_client_secret"
GITHUB_REDIRECT_URI="http://localhost:8000/auth/github/callback"
```

### 3. Setup Virtual Environment
```bash
python -m venv .venv
# Activate on Windows:
.venv\Scripts\activate
# Activate on macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Database Migrations Initialization
Populate the SQLite database schemas using Alembic:
```bash
alembic upgrade head
```

### 5. Launch Development Server
```bash
uvicorn app.main:app --reload
```
Open `http://localhost:8000` to interact with your local platform. Swagger REST docs are available at `http://localhost:8000/docs`.

---

## 🚀 Deployment Strategy

For cloud-based production environments (e.g. AWS, Render, Heroku):
1. **Containerization**: Deploy using a standardized multi-stage Docker build separating Python build requirements.
2. **Stateless Web**: Ensure the FastAPI server is stateless. Sync jobs queue resides in-memory (scalable in production using standard Celery / Redis background worker frameworks).
3. **Database**: Swap SQLite out for PostgreSQL by configuring `DATABASE_URL=postgresql://user:pass@host/db` in env variables.

---

## 🗺️ Development Roadmap

* [x] **Phase 1: Core Analytical Engine** — SQLite structures, paginated incremental sync workers, and baseline dashboard charts.
* [x] **Phase 2: Modular AI Workspace** — Decoupled client-side static libraries and secure symmetric BYOK API key models.
* [ ] **Phase 3: Shared Capabilities** — Multi-tenant organization support, Slack webhook notifications, and scheduled background cron synchronizations.

---

## 📄 License & Attribution

This project is licensed under the terms of the MIT License. See [LICENSE](LICENSE) for details.

Developed with 💻 and ☕ by [kh4i-dev](https://github.com/kh4i-dev). Vietnamese Tech Thesis reference material and documentation available under [docs/architecture/cong-nghe-va-kien-truc.md](docs/architecture/cong-nghe-va-kien-truc.md).
