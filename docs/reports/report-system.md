# Git Analytics — Engineering Report System

---

## Overview

Engineering Reports are immutable snapshots of repository analytics at a point in time. They combine release notes, changelog, risk insights, and summary context into one canonical report object. Reports are the core distribution mechanism, shareable via capability URL.

---

## Core Concepts

### Report Object
- Belongs to exactly one Repository
- Owned by exactly one User
- Has a **Report Date Range** (`from_date`, `to_date`)
- Has an **As-of Date** (generation timestamp)
- Immutable — state does not change after generation

### Titles
- **Generated Report Title**: Auto-assigned (repo name + date range)
- **Custom Report Title**: Optional user-edited display title
- **Display Title**: `custom_title ?? generated_title` — custom takes precedence when set

### Report Contents
- Release notes (AI-summarized or system compiled)
- Changelog (categorized commit updates)
- Risk insights (stagnation warnings, single-contributor bottlenecks, high-churn files)
- Summary metrics (commits, PRs, issues, contributors)
- Health score snapshot
- All data serialized at generation time

---

## Public Sharing

### Capability URL
- Long random token in URL grants anonymous read access
- Non-indexed (`noindex, nofollow` meta tags)
- Non-expiring by default

### Revocation
- **Revoke ≠ Delete**: Removes public access, keeps private report
- Revoked tokens return 404 (not 410) — indistinguishable from invalid tokens
- **Token Rotation**: Republish after revoke creates a new token
- Revoked tokens are never reused

### Anonymization
- Report-level setting to hide repository name in public view
- Does NOT mutate the Repository data
- Anonymized reports show configured public display name or "Private Repository"

---

## Report Management

| Action | Effect |
|---|---|
| Generate | Create new immutable snapshot from synced data |
| Edit Title | Update `custom_title` (does not overwrite `generated_title`) |
| Revoke | Remove public access (private report kept) |
| Republish | Create new public token (old token stays invalid) |
| Delete | Permanently remove report (destructive) |

---

## Data Flow

```
User → Route → EngineeringReportService
  → Fetch current analytics state (AnalyticsService)
  → Generate release notes (ReleaseNotesService)
  → Generate changelog (ChangelogService)
  → Compute risk insights (RiskInsightService)
  → Serialize all data as snapshot → DB
  → Return report object
```

---

## Stale Data

- **Stale Data Threshold**: Configurable age after which synced data is treated as stale
- Generation reads from DB — does not trigger new sync
- Warning shown if data is stale at generation time
