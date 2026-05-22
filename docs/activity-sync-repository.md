# Activity Diagram — Luồng đồng bộ Repository

---

## 1. Tổng quan luồng Sync

Khi User nhấn nút Sync, hệ thống thực hiện đồng bộ dữ liệu từ GitHub API gồm commits, pull requests và issues.

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
stateDiagram-v2
    direction TB
    
    state "User click Sync" as start
    state "Kiem tra xac thuc" as auth_check
    state "Kiem tra repo ownership" as owner_check
    state "Kiem tra sync status" as status_check
    state "Da sync? Huy" as already_syncing
    state "Kiem tra rate limit" as rate_check
    state "Quota du?" as quota_decision
    state "Quota thieu? Thong bao" as quota_warn
    state "Set status = syncing" as set_syncing
    state "Set sync_started_at" as set_started
    
    state "Xac dinh mode" as mode_decision
    state "Full sync" as full_mode
    state "Incremental sync" as inc_mode
    
    state "Fetch commits" as fetch_commits
    state "Fetch pull requests" as fetch_prs
    state "Fetch issues" as fetch_issues
    
    state "Kiem tra Link header" as link_check
    state "Con page?" as page_decision
    state "Fetch next page" as next_page
    
    state "Resolve contributors" as resolve_contrib
    state "Upsert contributors" as upsert_contrib
    state "Upsert commits" as upsert_commits
    state "Upsert PRs" as upsert_prs
    state "Upsert issues" as upsert_issues
    
    state "Co loi?" as error_decision
    state "Set status = failed" as set_failed
    state "Set last_sync_error" as set_error
    state "Gi? nguyen last_synced_at" as keep_last_sync
    state "Set status = success" as set_success
    state "Update last_synced_at" as update_last_sync
    state "Clear error" as clear_error
    
    state "Thong bao thanh cong" as notify_success
    state "Thong bao that bai" as notify_fail
    
    [*] --> start
    start --> auth_check
    auth_check --> owner_check
    owner_check --> status_check
    status_check --> already_syncing: dang syncing
    status_check --> rate_check: chua sync / da xong
    already_syncing --> [*]: Thong bao "dang sync"
    
    rate_check --> quota_decision
    quota_decision --> quota_warn: remaining < 50
    quota_decision --> set_syncing: remaining >= 50
    quota_warn --> [*]: Canh bao user
    
    set_syncing --> set_started
    set_started --> mode_decision
    
    mode_decision --> full_mode: last_synced_at == null
    mode_decision --> inc_mode: last_synced_at != null
    
    full_mode --> fetch_commits
    inc_mode --> fetch_commits
    
    fetch_commits --> page_decision
    page_decision --> next_page: con page
    page_decision --> fetch_prs: het page
    next_page --> fetch_commits
    
    fetch_prs --> fetch_issues
    fetch_issues --> resolve_contrib
    
    resolve_contrib --> upsert_contrib
    upsert_contrib --> upsert_commits
    upsert_commits --> upsert_prs
    upsert_prs --> upsert_issues
    
    upsert_issues --> error_decision
    
    error_decision --> set_failed: co loi (network, API, DB)
    error_decision --> set_success: khong loi
    
    set_failed --> set_error
    set_error --> keep_last_sync
    keep_last_sync --> notify_fail
    notify_fail --> [*]
    
    set_success --> update_last_sync
    update_last_sync --> clear_error
    clear_error --> notify_success
    notify_success --> [*]
```

</div>

---

## 2. Activity Diagram — Pre-sync Check

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
flowchart TD
    Start(["Bat dau Sync"]) --> Auth{"User da xac thuc?"}
    Auth -- "Khong" --> AuthFail["Chuyen huong login"]
    Auth -- "Co" --> Owner{"Repo thuoc ve user?"}
    Owner -- "Khong" --> OwnerFail["Bao loi 403"]
    Owner -- "Co" --> Status{"Trang thai sync?"}
    
    Status -- "dang syncing" --> Conflict["Bao loi 409<br>dang sync"]
    Status -- "pending / success / failed" --> RateLimit
    
    subgraph RateLimit["Kiem tra Rate Limit"]
        RL_Call["Goi GET /rate_limit"] --> RL_Check{"remaining >= 50?"}
        RL_Check -- "Khong" --> RL_Warn["Canh bao user<br>quota thieu"]
        RL_Check -- "Co" --> Proceed["Cho phep sync"]
    end
    
    Conflict --> End["Ket thuc"]
    RL_Warn --> End
```

</div>

---

## 3. Activity Diagram — Sync Mode Decision

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
flowchart TD
    Start(["Xac dinh mode"]) --> Check{"last_synced_at == null?"}
    
    Check -- "Yes (lan dau)" --> Full["Full Sync"]
    Full --> Full1["Khong co since parameter"]
    Full1 --> Full2["Fetch TOAN BO commits"]
    Full2 --> Full3["Fetch TOAN BO PRs"]
    Full3 --> Full4["Fetch TOAN BO issues"]
    Full4 --> Persist["Luu vao DB"]
    
    Check -- "No (da sync)" --> Inc["Incremental Sync"]
    Inc --> Inc1["since = last_synced_at.isoformat()"]
    Inc1 --> Inc2["Fetch commits since={since}"]
    Inc2 --> Inc3["Fetch PRs since={since}"]
    Inc3 --> Inc4["Fetch issues since={since}"]
    Inc4 --> Persist
    
    Persist --> End(["Hoan tat"])
```

</div>

---

## 4. Activity Diagram — Fetch với Pagination

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
flowchart TD
    Start(["Fetch commits"]) --> Page["Goi page = 1<br>per_page = 100"]
    Page --> Response["Nhan response"]
    Response --> CheckRate{"Kiem tra<br>X-RateLimit-Remaining"}
    
    CheckRate -- "== 0 -->" RateLimitErr["Raise<br>GitHubRateLimitExceeded"]
    CheckRate -- "> 0 -->" ParseLink["Doc Link header"]
    
    ParseLink --> HasNext{"Co rel=next?"}
    HasNext -- "Co -->" NextPage["Tang page<br>Goi page tiep theo"]
    NextPage --> Response
    
    HasNext -- "Khong -->" Done["Da lay het data"]
    Done --> End(["Tra ve danh sach"])
    
    RateLimitErr --> EndErr(["Dung sync<br>set status = failed"])
```

</div>

---

## 5. Activity Diagram — Upsert Data

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
flowchart TD
    Start(["Persist data"]) --> Resolve["Resolve contributors"]
    Resolve --> CheckLogin{"Co github_login?"}
    
    CheckLogin -- "Co" --> FindLogin["Tim contributor theo login"]
    CheckLogin -- "Khong" --> FindEmail["Tim contributor theo email"]
    
    FindLogin --> ExistsLogin{"Ton tai?"}
    FindEmail --> ExistsEmail{"Ton tai?"}
    
    ExistsLogin -- "Co" --> UpdateLogin["Update thong tin"]
    ExistsLogin -- "Khong" --> CreateLogin["Create moi"]
    
    ExistsEmail -- "Co" --> UpdateEmail["Update thong tin"]
    ExistsEmail -- "Khong" --> CreateEmail["Create moi"]
    
    UpdateLogin --> UpsertCommits
    CreateLogin --> UpsertCommits
    UpdateEmail --> UpsertCommits
    CreateEmail --> UpsertCommits
    
    subgraph UpsertCommits["Upsert commits"]
        UC1["For each commit"] --> UC2{"Ton tai<br>repo_id + sha?"}
        UC2 -- "Co" --> UC3["Skip (da co)"]
        UC2 -- "Khong" --> UC4["INSERT commit"]
    end
    
    UpsertCommits --> UpsertPRs
    
    subgraph UpsertPRs["Upsert pull requests"]
        UP1["For each PR"] --> UP2{"Ton tai<br>repo_id + number?"}
        UP2 -- "Co" --> UP3["UPDATE state/merged"]
        UP2 -- "Khong" --> UP4["INSERT PR"]
    end
    
    UpsertPRs --> UpsertIssues
    
    subgraph UpsertIssues["Upsert issues"]
        UI1["For each issue"] --> UI2{"Ton tai<br>repo_id + number?"}
        UI2 -- "Co" --> UI3["UPDATE state/labels"]
        UI2 -- "Khong" --> UI4["INSERT issue"]
    end
    
    UpsertIssues --> UpdateStatus
    
    UpdateStatus["Update last_synced_at"] --> End(["Hoan tat"])
```

</div>

---

## 6. Activity Diagram — Xử lý lỗi

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
flowchart TD
    Error["Loi xay ra"] --> Type{"Loai loi?"}
    
    Type -- "Rate Limit" --> RL["Set status = failed"]
    Type -- "Network Error" --> Net["Set status = failed"]
    Type -- "GitHub API Error" --> GH["Set status = failed"]
    Type -- "DB Error" --> DB["Set status = failed"]
    
    RL --> Msg["Ghi last_sync_error<br>= 'Rate limit exceeded'"]
    Net --> Msg2["Ghi last_sync_error<br>= 'Network error: timeout'"]
    GH --> Msg3["Ghi last_sync_error<br>= 'GitHub API: 500'"]
    DB --> Msg4["Ghi last_sync_error<br>= 'Database constraint'"]
    
    Msg --> Keep["GIU NGUYEN last_synced_at"]
    Msg2 --> Keep
    Msg3 --> Keep
    Msg4 --> Keep
    
    Keep --> Notify["Thong bao cho user"]
    Notify --> Retry{"User nhan<br>Sync lai?"}
    
    Retry -- "Co" --> RetrySync["Sync tu same point<br>(incremental)"]
    Retry -- "Khong" --> End(["Ket thuc"])
    
    RetrySync --> End
```

</div>

---

## 7. Activity Diagram Tổng Hợp

<div style="background: white; padding: 16px; border-radius: 8px;">

```mermaid
flowchart TB
    subgraph PreCheck["1. Pre-sync Check"]
        direction TB
        A1["Kiem tra auth"] --> A2["Kiem tra ownership"]
        A2 --> A3["Kiem tra status"]
        A3 --> A4["Kiem tra rate limit"]
    end
    
    subgraph Sync["2. Sync Process"]
        direction TB
        B1["Set status = syncing"] --> B2["Xac dinh full/incremental"]
        B2 --> B3["Fetch commits (paginated)"]
        B3 --> B4["Fetch PRs"]
        B4 --> B5["Fetch issues"]
    end
    
    subgraph Persist["3. Persist Data"]
        direction TB
        C1["Resolve contributors"] --> C2["Upsert contributors"]
        C2 --> C3["Upsert commits"]
        C3 --> C4["Upsert PRs"]
        C4 --> C5["Upsert issues"]
    end
    
    subgraph Final["4. Finalize"]
        direction TB
        D1{"Co loi?"} -- "Khong" --> D2["Set status = success"]
        D1 -- "Co" --> D3["Set status = failed"]
        D2 --> D4["Update last_synced_at"]
        D3 --> D5["Giu nguyen last_synced_at"]
        D4 --> D6["Clear error"]
        D5 --> D7["Ghi last_sync_error"]
    end
    
    PreCheck --> Sync
    Sync --> Persist
    Persist --> Final
```

</div>
