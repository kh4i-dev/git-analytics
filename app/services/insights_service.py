from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import RepositoryNotFoundException
from app.repositories import (
    CommitRepository,
    IssueRepository,
    PullRequestRepository,
    RepositoryRepository,
)


class InsightsService:
    def __init__(self, db: Session) -> None:
        self.commit_repo = CommitRepository(db)
        self.pr_repo = PullRequestRepository(db)
        self.issue_repo = IssueRepository(db)
        self.repo_repo = RepositoryRepository(db)

    def _get_repo(self, user_id: int, repo_id: int):
        repo = self.repo_repo.get_by_user_and_id(user_id, repo_id)
        if repo is None:
            raise RepositoryNotFoundException("Repository not found.")
        return repo

    def get_insights(
        self,
        user_id: int,
        repo_id: int,
        branch_filter: str | None = None,
    ) -> dict[str, Any]:
        repo = self._get_repo(user_id, repo_id)

        cpd = self.commit_repo.commits_per_day(repo_id, branch_filter)
        weekday_data = self.commit_repo.commits_by_weekday(repo_id, branch_filter)
        hour_data = self.commit_repo.commits_by_hour(repo_id, branch_filter)
        messages = self.commit_repo.get_recent_messages(
            repo_id,
            limit=500,
            branch_filter=branch_filter,
        )
        prs = self.pr_repo.list_by_repo(
            repo_id,
            page=1,
            per_page=100,
            branch_filter=branch_filter,
        )
        issues = self.issue_repo.list_by_repo(repo_id, page=1, per_page=100)

        heatmap = _build_heatmap(cpd)
        coding = _coding_activity(cpd, weekday_data, hour_data, heatmap)
        commit_intel = _commit_intelligence(cpd, messages, weekday_data)
        pr_intel = _pr_intelligence(list(prs))
        issue_intel = _issue_intelligence(list(issues))
        score = _activity_score(cpd, list(prs), list(issues))

        return {
            "repository": {
                "id": repo.id,
                "full_name": repo.full_name,
                "last_synced_at": repo.last_synced_at.isoformat() if repo.last_synced_at else None,
            },
            "branch_filter": branch_filter or "all",
            "activity_score": score,
            "heatmap": heatmap,
            "coding_activity": coding,
            "commit_intelligence": commit_intel,
            "pr_intelligence": pr_intel,
            "issue_intelligence": issue_intel,
        }


# ── Heatmap ───────────────────────────────────────────────────────────────────

def _build_heatmap(cpd: list[dict]) -> dict[str, int]:
    date_map = {d["date"]: d["count"] for d in cpd}
    today = date.today()
    return {
        (today - timedelta(days=i)).isoformat(): date_map.get(
            (today - timedelta(days=i)).isoformat(), 0
        )
        for i in range(364, -1, -1)
    }


# ── Streaks ───────────────────────────────────────────────────────────────────

def _compute_streaks(cpd: list[dict]) -> tuple[int, int]:
    active = {d["date"] for d in cpd if d["count"] > 0}
    if not active:
        return 0, 0

    today = date.today()

    # current streak – walk backwards from today (or yesterday if today has nothing)
    current = 0
    cursor = today
    if cursor.isoformat() not in active:
        cursor -= timedelta(days=1)
    while cursor.isoformat() in active:
        current += 1
        cursor -= timedelta(days=1)

    # longest streak
    sorted_dates = sorted(date.fromisoformat(d) for d in active)
    longest = cur = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 1

    return current, longest


# ── Coding activity ───────────────────────────────────────────────────────────

def _coding_activity(
    cpd: list[dict],
    weekday_data: list[dict],
    hour_data: list[dict],
    heatmap: dict[str, int],
) -> dict[str, Any]:
    current_streak, longest_streak = _compute_streaks(cpd)

    total_commits = sum(d["count"] for d in cpd)
    active_days = sum(1 for d in cpd if d["count"] > 0)
    avg_per_day = round(total_commits / active_days, 1) if active_days else 0

    # Most active weekday
    most_active_day = max(weekday_data, key=lambda x: x["count"], default=None)

    # Peak hour band
    peak_hour = max(hour_data, key=lambda x: x["count"], default=None)
    peak_band = _hour_to_band(peak_hour["hour"]) if peak_hour and peak_hour["count"] > 0 else None

    # Busiest month (from cpd)
    month_counts: dict[str, int] = {}
    for d in cpd:
        month = d["date"][:7]  # "YYYY-MM"
        month_counts[month] = month_counts.get(month, 0) + d["count"]
    busiest_month = max(month_counts, key=lambda k: month_counts[k]) if month_counts else None

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "active_days": active_days,
        "avg_commits_per_active_day": avg_per_day,
        "most_active_day": most_active_day["day"] if most_active_day else None,
        "most_active_day_count": most_active_day["count"] if most_active_day else 0,
        "peak_hour_band": peak_band,
        "peak_hour": peak_hour["hour"] if peak_hour else None,
        "busiest_month": busiest_month,
        "weekday_data": weekday_data,
        "hour_data": hour_data,
    }


def _hour_to_band(hour: int) -> str:
    if 6 <= hour < 12:
        return "Sáng (6–12)"
    if 12 <= hour < 18:
        return "Chiều (12–18)"
    if 18 <= hour < 22:
        return "Tối (18–22)"
    return "Đêm (22–6)"


# ── Commit intelligence ───────────────────────────────────────────────────────

def _commit_intelligence(
    cpd: list[dict],
    messages: list[str],
    weekday_data: list[dict],
) -> dict[str, Any]:
    total = sum(d["count"] for d in cpd)

    # Keyword analysis (conventional commits)
    keywords = {k: 0 for k in ["feat", "fix", "refactor", "docs", "chore", "test", "style", "perf"]}
    unclassified = 0
    for msg in messages:
        matched = False
        lower = (msg or "").lower().strip()
        for kw in keywords:
            if lower.startswith(kw + ":") or lower.startswith(kw + "("):
                keywords[kw] += 1
                matched = True
                break
        if not matched:
            unclassified += 1

    # Trend: last 4 weeks vs previous 4 weeks
    today = date.today()
    four_w = (today - timedelta(weeks=4)).isoformat()
    eight_w = (today - timedelta(weeks=8)).isoformat()
    recent_4w = sum(d["count"] for d in cpd if d["date"] >= four_w)
    prev_4w = sum(d["count"] for d in cpd if eight_w <= d["date"] < four_w)
    trend_pct = None
    if prev_4w > 0:
        trend_pct = round((recent_4w - prev_4w) / prev_4w * 100)
    elif recent_4w > 0:
        trend_pct = 100

    # Busiest weekday name
    top_day = max(weekday_data, key=lambda x: x["count"], default=None)

    return {
        "total_commits": total,
        "keywords": {k: v for k, v in sorted(keywords.items(), key=lambda x: x[1], reverse=True)},
        "unclassified": unclassified,
        "recent_4w": recent_4w,
        "trend_pct": trend_pct,
        "top_weekday": top_day["day"] if top_day else None,
    }


# ── PR intelligence ───────────────────────────────────────────────────────────

def _pr_intelligence(prs: list) -> dict[str, Any]:
    total = len(prs)
    merged = sum(1 for p in prs if p.is_merged)
    open_list = [p for p in prs if p.state == "open" and not p.is_merged]

    merge_times_h: list[float] = []
    for p in prs:
        if p.merged_at and p.created_at:
            merge_times_h.append((p.merged_at - p.created_at).total_seconds() / 3600)
    avg_merge_h = round(sum(merge_times_h) / len(merge_times_h), 1) if merge_times_h else None

    now = datetime.now(UTC).replace(tzinfo=None)
    ages = []
    for p in open_list:
        if p.created_at:
            p_created = p.created_at.replace(tzinfo=None) if p.created_at.tzinfo else p.created_at
            ages.append((now - p_created).total_seconds() / 3600 / 24)
    avg_age_days = round(sum(ages) / len(ages), 1) if ages else None

    # Throughput: PRs per week over the dataset span
    if len(prs) >= 2:
        dates = sorted(p.created_at for p in prs if p.created_at)
        if len(dates) >= 2:
            span_weeks = max((dates[-1] - dates[0]).days / 7, 1)
            throughput = round(total / span_weeks, 1)
        else:
            throughput = None
    else:
        throughput = None

    success_ratio = round(merged / total * 100) if total else 0

    return {
        "total": total,
        "merged": merged,
        "open": len(open_list),
        "success_ratio_pct": success_ratio,
        "avg_merge_time_hours": avg_merge_h,
        "avg_merge_time_display": _fmt_duration_h(avg_merge_h),
        "avg_pr_age_days": avg_age_days,
        "throughput_per_week": throughput,
    }


# ── Issue intelligence ────────────────────────────────────────────────────────

def _issue_intelligence(issues: list) -> dict[str, Any]:
    total = len(issues)
    open_i = sum(1 for i in issues if i.state == "open")
    closed_i = sum(1 for i in issues if i.state == "closed")

    resolve_times_h: list[float] = []
    for i in issues:
        if i.closed_at and i.created_at:
            resolve_times_h.append((i.closed_at - i.created_at).total_seconds() / 3600)
    avg_resolve_h = round(sum(resolve_times_h) / len(resolve_times_h), 1) if resolve_times_h else None

    bug_labels = {"bug", "bug report", "defect", "error", "regression", "crash"}
    feat_labels = {"enhancement", "feature", "feature request", "new feature", "improvement"}
    bug_count = 0
    feature_count = 0
    for issue in issues:
        lower_labels = {(lb or "").lower() for lb in (issue.labels or [])}
        if lower_labels & bug_labels:
            bug_count += 1
        elif lower_labels & feat_labels:
            feature_count += 1

    closure_rate = round(closed_i / total * 100) if total else 0

    return {
        "total": total,
        "open": open_i,
        "closed": closed_i,
        "closure_rate_pct": closure_rate,
        "avg_resolution_hours": avg_resolve_h,
        "avg_resolution_display": _fmt_duration_h(avg_resolve_h),
        "bug_count": bug_count,
        "feature_count": feature_count,
        "bug_ratio_pct": round(bug_count / total * 100) if total else 0,
    }


# ── Activity score ────────────────────────────────────────────────────────────

def _activity_score(cpd: list[dict], prs: list, issues: list) -> dict[str, Any]:
    today = date.today()
    cutoff = (today - timedelta(days=30)).isoformat()

    commits_30d = sum(d["count"] for d in cpd if d["date"] >= cutoff)

    now_naive = datetime.now(UTC).replace(tzinfo=None)
    cutoff_dt = now_naive - timedelta(days=30)

    prs_30d = 0
    for p in prs:
        if p.created_at:
            p_created = p.created_at.replace(tzinfo=None) if p.created_at.tzinfo else p.created_at
            if p_created >= cutoff_dt:
                prs_30d += 1

    issues_30d = 0
    for i in issues:
        if i.created_at:
            i_created = i.created_at.replace(tzinfo=None) if i.created_at.tzinfo else i.created_at
            if i_created >= cutoff_dt:
                issues_30d += 1

    raw = commits_30d * 2 + prs_30d * 5 + issues_30d * 3
    score = min(100, raw)

    level = "Low"
    if score >= 70:
        level = "High"
    elif score >= 35:
        level = "Medium"

    return {
        "score": score,
        "level": level,
        "commits_30d": commits_30d,
        "prs_30d": prs_30d,
        "issues_30d": issues_30d,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_duration_h(hours: float | None) -> str | None:
    if hours is None:
        return None
    if hours < 1:
        return f"{int(hours * 60)} phút"
    if hours < 24:
        return f"{hours:.1f} giờ"
    days = hours / 24
    return f"{days:.1f} ngày"
