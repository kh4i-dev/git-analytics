# Git Analytics — Analytics & KPI Calculation Guide

This document defines the mathematical models, formulas, streak tracking rules, health scoring systems, and global dashboard aggregation structures powering the Git Analytics engine.

---

## 1. Core KPIs and Formulas

Git Analytics aggregates raw synchronized database entities (commits, pull requests, issues) into actionable engineering performance indicators.

### A. Cycle Times

* **Average Pull Request Merge Time (Hours)**:
  Measures the duration from PR creation to merge event.
  $$\text{Average Merge Time} = \frac{\sum_{i=1}^{N} (T_{\text{merged}, i} - T_{\text{created}, i})}{N_{\text{merged}}}$$
  *Where $T_{\text{merged}, i}$ and $T_{\text{created}, i}$ are timezone-aware UTC timestamps of merged PRs within the range.*

* **Average Issue Closure Time (Hours)**:
  Measures the duration from issue creation to close event.
  $$\text{Average Closure Time} = \frac{\sum_{j=1}^{M} (T_{\text{closed}, j} - T_{\text{created}, j})}{M_{\text{closed}}}$$

### B. Code Velocity & Activity

* **Commit Density / Frequency**:
  Total commits grouped by calendar day (UTC) to plot activity graphs over 7-day, 30-day, and custom period ranges.
* **Contribution Breakdown**:
  Aggregates total commits, pull requests merged, issues opened/closed, and active days per Contributor to render performance leaderboards.

---

## 2. Streak Calculations

Streak tracking encourages consistent development habits. The calculation walks through daily calendar activity:

* **Active Day**: Any calendar day (UTC timezone) containing at least 1 commit.
* **Current Streak**:
  * Walks backward chronologically starting from `today`.
  * If `today` contains zero contributions, the algorithm checks `yesterday`.
  * If `yesterday` also contains zero contributions, the current streak is instantly evaluated as `0`.
  * If either `today` or `yesterday` is active, it counts backward consecutively until it encounters the first inactive gap day.
* **Longest Streak**:
  * Scans the historical timeline of active days.
  * Calculates the size of all contiguous blocks of consecutive active contribution days.
  * Evaluates the maximum contiguous block size.

---

## 3. Repository Health Score Model

The **Repository Health Score** is a consolidated rating (from 0 to 100) that gives managers and developers a quick indicator of codebase vitality.

$$\text{Health Score} = S_{\text{commits}} + S_{\text{PRs}} + S_{\text{issues}} + S_{\text{streaks}}$$

### Score Weight Allocations (Maximum 100 points)

1. **Commit Activity ($S_{\text{commits}}$ - Max 40 points)**:
   * Evaluated based on total commits in the active period.
   * Scaled logarithmically or linearly up to a threshold (e.g. 5 commits/week).
2. **PR Turnaround ($S_{\text{PRs}}$ - Max 30 points)**:
   * High points awarded for fast average merge times (under 24 hours).
   * Degrades as average merge times stretch past 72 hours.
3. **Issue Resolution Efficiency ($S_{\text{issues}}$ - Max 20 points)**:
   * Higher points for high issue closure-to-opening ratios.
   * Penalized for high volumes of stale/unresolved issues.
4. **Contribution Consistency ($S_{\text{streaks}}$ - Max 10 points)**:
   * Points awarded based on the current active streak length.
   * Maintaining a streak of 3+ days boosts health scores.

---

## 4. Global Cross-Repository Dashboard

For engineering leaders managing multiple software assets, Git Analytics supports a **Global / Cross-Repository Dashboard** that aggregates metadata across all connected workspaces.

```
                  ┌──────────────────────┐
                  │ Connected Repository │
                  └──────────┬───────────┘
                             │ (SQLite/PG Metadata)
                             ▼
┌──────────────────────────────────────────────────────────┐
│                   GLOBAL AGGREGATION                     │
├──────────────────────────────────────────────────────────┤
│ Aggregated KPIs:                                         │
│ - Total Commits across all Repositories                  │
│ - Total PRs (Merged, Open, Closed)                       │
│ - Total Open & Closed Issues                             │
│ - Multi-Repo Contributor Leaderboard                     │
│ - Unified Activity Timeline Heatmap                      │
└──────────────────────────────────────────────────────────┘
```

* **Dynamic Filters**: Allows users to filter data across all repositories, single repositories, specific authors, or specific branches.
* **Unified Heatmaps**: Merges commit activities from multiple repositories to show global hour-of-day and day-of-week contribution schedules.
