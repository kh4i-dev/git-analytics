# Sequence Diagram — Xử lý API Analytics

---

## 1. Tổng quan luồng xử lý

Khi User mở một trang dashboard, browser gọi page route để lấy HTML skeleton, sau đó fetch song song các API endpoints để lấy dữ liệu và render Chart.js.

```mermaid
sequenceDiagram
    participant U as User
    participant B as Browser
    participant P as Page Route
    participant A as API Route
    participant S as AnalyticsService
    participant R as Repository Layer
    participant DB as Database

    U->>B: Mở Dashboard
    B->>P: GET /dashboard/overview/{repo_id}
    P->>B: HTML skeleton (loading state)
    
    Note over B,A: Fetch song song cac API
    B->>A: fetch /api/v1/analytics/{repo_id}/summary
    B->>A: fetch /api/v1/analytics/{repo_id}/commits
    B->>A: fetch /api/v1/analytics/{repo_id}/pulls
    B->>A: fetch /api/v1/analytics/{repo_id}/issues
    
    A->>S: get_summary_metrics(repo_id)
    S->>R: RepositoryRepo.get_by_id(repo_id)
    R->>DB: SELECT * FROM repositories WHERE id = ?
    DB->>R: Repository data
    R->>S: repository
    
    S->>R: get_commit_stats(repo_id)
    R->>DB: SELECT COUNT(*), DATE(created_at)<br>FROM commits<br>WHERE repo_id = ?<br>GROUP BY DATE(created_at)
    DB->>R: Aggregated rows
    R->>S: commit stats
    
    S->>R: get_pr_stats(repo_id)
    R->>DB: SELECT state, COUNT(*), AVG(merge_time)<br>FROM pull_requests<br>WHERE repo_id = ?<br>GROUP BY state
    DB->>R: PR stats
    R->>S: PR stats
    
    S->>R: get_issue_stats(repo_id)
    R->>DB: SELECT state, COUNT(*)<br>FROM issues<br>WHERE repo_id = ?<br>GROUP BY state
    DB->>R: Issue stats
    R->>S: Issue stats
    
    S->>A: { summary, commits, pulls, issues }
    A->>B: JSON response { data: {...}, meta: {...} }
    
    B->>B: Chart.js render charts
    B->>U: Hien thi dashboard hoan chinh
```

---

## 2. Luồng xử lý Contributor Analytics

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as API Route
    participant S as AnalyticsService
    participant R as Repository Layer
    participant DB as Database

    B->>A: GET /api/v1/analytics/{repo_id}/contributors
    A->>S: get_contributor_metrics(repo_id)
    S->>R: get_contributors_by_repo(repo_id)
    R->>DB: SELECT * FROM contributors WHERE repo_id = ?
    DB->>R: List contributors
    R->>S: contributors list
    
    loop For each contributor
        S->>R: get_contributor_commit_stats(contributor_id, repo_id)
        R->>DB: SELECT COUNT(*), SUM(additions), SUM(deletions)<br>FROM commits<br>WHERE contributor_id = ? AND repo_id = ?
        DB->>R: commit stats
        
        S->>R: get_contributor_pr_stats(contributor_id, repo_id)
        R->>DB: SELECT COUNT(*), AVG(merge_time)<br>FROM pull_requests<br>WHERE author_id = ? AND repo_id = ?
        DB->>R: PR stats
        
        S->>R: get_contributor_issue_stats(contributor_id, repo_id)
        R->>DB: SELECT COUNT(*)<br>FROM issues<br>WHERE author_id = ? AND repo_id = ?
        DB->>R: issue stats
    end
    
    S->>A: { contributors: [{ login, avatar, commits, prs, issues }] }
    A->>B: JSON response
```

---

## 3. Luồng xử lý Branch Analytics

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as API Route
    participant S as AnalyticsService
    participant R as Repository Layer
    participant DB as Database

    B->>A: GET /api/v1/analytics/{repo_id}/branches
    A->>S: get_branch_metrics(repo_id)
    S->>R: get_branches(repo_id)
    R->>DB: SELECT DISTINCT branch FROM commits WHERE repo_id = ?
    DB->>R: branch list
    R->>S: [main, dev, feature/x, ...]
    
    B->>A: GET /api/v1/analytics/{repo_id}/commits?branch=feature/x
    A->>S: get_commit_metrics(repo_id, branch="feature/x")
    S->>R: get_commit_stats_by_branch(repo_id, branch)
    R->>DB: SELECT COUNT(*), DATE(created_at)<br>FROM commits<br>WHERE repo_id = ? AND branch = ?<br>GROUP BY DATE(created_at)
    DB->>R: commits by date for branch
    R->>S: branch commit stats
    S->>A: { commits_by_date: [...], total: N }
    A->>B: JSON response
```

---

## 4. Luồng xử lý Insights (Heatmap + Streaks)

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as API Route
    participant S as AnalyticsService
    participant R as Repository Layer
    participant DB as Database

    B->>A: GET /api/v1/insights/{repo_id}
    A->>S: get_insights(repo_id)
    
    S->>R: get_heatmap_data(repo_id)
    R->>DB: SELECT DATE(created_at), COUNT(*)<br>FROM commits<br>WHERE repo_id = ?<br>AND created_at >= DATE('now', '-365 days')<br>GROUP BY DATE(created_at)
    DB->>R: 365-day heatmap data
    R->>S: [{ date: "2024-01-01", count: 5 }, ...]
    
    S->>R: get_streak_data(repo_id)
    R->>DB: SELECT DISTINCT DATE(created_at) as day<br>FROM commits<br>WHERE repo_id = ?<br>ORDER BY day DESC
    DB->>R: commit days
    R->>S: streak calculation
    
    S->>R: get_hour_distribution(repo_id)
    R->>DB: SELECT CAST(strftime('%H', created_at) AS INTEGER) as hour, COUNT(*)<br>FROM commits<br>WHERE repo_id = ?<br>GROUP BY hour
    DB->>R: commits by hour
    
    S->>R: get_weekday_distribution(repo_id)
    R->>DB: SELECT CAST(strftime('%w', created_at) AS INTEGER) as weekday, COUNT(*)<br>FROM commits<br>WHERE repo_id = ?<br>GROUP BY weekday
    DB->>R: commits by weekday
    
    S->>A: { heatmap, streaks, hour_dist, weekday_dist, health_score }
    A->>B: JSON response
```

---

## 5. Luồng xử lý Executive Overview

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as API Route
    participant S as AnalyticsService
    participant R as Repository Layer
    participant DB as Database

    B->>A: GET /api/v1/analytics/{repo_id}/executive
    A->>S: get_executive_overview(repo_id)
    
    S->>R: get_health_score(repo_id)
    R->>DB: SELECT<br>    AVG(daily_commit_freq) as commit_score,<br>    AVG(pr_merge_rate) as pr_score,<br>    AVG(issue_closure_rate) as issue_score<br>FROM repo_metrics<br>WHERE repo_id = ?
    DB->>R: composite scores
    R->>S: health_score (0-100)
    
    S->>R: get_velocity_metrics(repo_id)
    R->>DB: SELECT<br>    COUNT(*) as total_commits,<br>    AVG(additions) as avg_additions,<br>    AVG(deletions) as avg_deletions<br>FROM commits<br>WHERE repo_id = ?
    DB->>R: velocity data
    
    S->>R: get_contributor_count(repo_id)
    R->>DB: SELECT COUNT(DISTINCT contributor_id)<br>FROM commits WHERE repo_id = ?
    DB->>R: total contributors
    
    S->>R: get_trend_data(repo_id)
    R->>DB: SELECT DATE(created_at), COUNT(*)<br>FROM commits<br>WHERE repo_id = ?<br>GROUP BY DATE(created_at)<br>ORDER BY DATE(created_at)<br>LIMIT 30
    DB->>R: 30-day trend
    
    S->>A: { health_score, velocity, contributors, trends }
    A->>B: JSON response
```

---

## 6. API Response Format

Tat ca API analytics tra ve cung mot format:

```json
{
  "data": {
    "commits": { "total": 150, "by_date": [...] },
    "pulls": { "open": 5, "merged": 20, "closed": 3 },
    "issues": { "open": 8, "closed": 15 }
  },
  "error": null,
  "meta": {
    "trace_id": "abc-123-def",
    "timestamp": "2024-06-15T10:30:00Z"
  }
}
```

---

## 7. Sequence Diagram Tổng Hợp

```mermaid
sequenceDiagram
    participant U as User
    participant B as Browser
    participant P as Page Route
    participant API as API Routes
    participant Svc as Services
    participant Repo as Repository Layer
    participant DB as Database

    rect rgb(240, 240, 240)
        Note over U,DB: 1. Page Load
        U->>B: Click menu item
        B->>P: GET page route
        P->>B: HTML skeleton + loading spinner
    end
    
    rect rgb(230, 240, 250)
        Note over U,DB: 2. Data Fetch (async)
        par Fetch summary
            B->>API: GET /api/v1/analytics/{id}/summary
        and Fetch commits
            B->>API: GET /api/v1/analytics/{id}/commits
        and Fetch PRs
            B->>API: GET /api/v1/analytics/{id}/pulls
        and Fetch issues
            B->>API: GET /api/v1/analytics/{id}/issues
        end
    end
    
    rect rgb(250, 240, 230)
        Note over U,DB: 3. Service Processing
        API->>Svc: Orchestrate queries
        Svc->>Repo: Aggregation queries
        Repo->>DB: SQL with GROUP BY
        DB->>Repo: Aggregated rows
        Repo->>Svc: typed results
        Svc->>API: formatted response
        API->>B: JSON { data, meta }
    end
    
    rect rgb(240, 250, 240)
        Note over U,DB: 4. Render
        B->>B: Chart.js render
        B->>B: Update cards
        B->>B: Hide loading
        B->>U: Complete dashboard
    end
```
