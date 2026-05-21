from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationException, RepositoryNotFoundException
from app.utils.timezone import isoformat_vn as _vn_iso
from app.models.repository import Repository
from app.models.branch import Branch
from app.models.commit import Commit
from app.models.pull_request import PullRequest
from app.models.issue import Issue
from app.models.contributor import Contributor
from app.repositories import (
    CommitRepository,
    ContributorRepository,
    IssueRepository,
    PullRequestRepository,
    RepositoryRepository,
)


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo_repo = RepositoryRepository(db)
        self.commit_repo = CommitRepository(db)
        self.pr_repo = PullRequestRepository(db)
        self.issue_repo = IssueRepository(db)
        self.contributor_repo = ContributorRepository(db)

    def get_global_overview(self, user_id: int) -> dict[str, Any]:
        repos = self.repo_repo.list_by_user(user_id, page=1, per_page=100)
        repo_ids = [repo.id for repo in repos]
        total_repos = len(repos)
        synced_repos = sum(1 for r in repos if r.last_sync_status == "success")
        private_repos = sum(1 for r in repos if r.is_private)
        public_repos = total_repos - private_repos

        total_commits = self.db.scalar(
            select(func.count(Commit.id))
            .join(Repository)
            .where(Repository.user_id == user_id)
        ) or 0

        total_prs = self.db.scalar(
            select(func.count(PullRequest.id))
            .join(Repository)
            .where(Repository.user_id == user_id)
        ) or 0

        total_issues = self.db.scalar(
            select(func.count(Issue.id))
            .join(Repository)
            .where(Repository.user_id == user_id)
        ) or 0

        total_contributors = self.db.scalar(
            select(func.count(func.distinct(func.coalesce(Contributor.github_login, Contributor.display_name))))
            .join(Repository)
            .where(Repository.user_id == user_id)
        ) or 0

        most_active_rows = self.db.execute(
            select(
                Repository.id,
                Repository.full_name,
                Repository.html_url,
                func.count(Commit.id).label("commit_count")
            )
            .join(Commit, Repository.id == Commit.repo_id)
            .where(Repository.user_id == user_id)
            .group_by(Repository.id, Repository.full_name, Repository.html_url)
            .order_by(func.count(Commit.id).desc())
            .limit(5)
        ).all()
        most_active = [
            {
                "id": row.id,
                "full_name": row.full_name,
                "html_url": row.html_url,
                "commit_count": row.commit_count,
            }
            for row in most_active_rows
        ]

        sync_activity_repos = self.db.scalars(
            select(Repository)
            .where(Repository.user_id == user_id, Repository.last_synced_at.is_not(None))
            .order_by(Repository.last_synced_at.desc())
            .limit(5)
        ).all()
        latest_syncs = [
            {
                "id": r.id,
                "full_name": r.full_name,
                "last_synced_at": _vn_iso(r.last_synced_at),
                "last_sync_status": r.last_sync_status,
            }
            for r in sync_activity_repos
        ]

        timeline_rows = self.db.execute(
            select(
                func.date(Commit.committed_at).label("date"),
                func.count(Commit.id).label("count")
            )
            .join(Repository)
            .where(Repository.user_id == user_id)
            .group_by(func.date(Commit.committed_at))
            .order_by(func.date(Commit.committed_at))
        ).all()
        global_commits_per_day = [{"date": str(row.date), "count": row.count} for row in timeline_rows][-30:]

        # --- Advanced Analytics for Phase B ---
        # 1. Active vs Inactive Repositories
        repo_commit_counts = self.db.execute(
            select(Repository.id, func.count(Commit.id).label("c_count"))
            .outerjoin(Commit, Repository.id == Commit.repo_id)
            .where(Repository.user_id == user_id)
            .group_by(Repository.id)
        ).all()
        active_repos_count = sum(1 for row in repo_commit_counts if row.c_count > 0)
        inactive_repos_count = total_repos - active_repos_count

        # 2. Commits last 7 days
        seven_days_ago = datetime.now(UTC) - timedelta(days=7)
        commits_last_7 = self.db.scalar(
            select(func.count(Commit.id))
            .join(Repository)
            .where(Repository.user_id == user_id, Commit.committed_at >= seven_days_ago)
        ) or 0

        # 3. Top Contributor
        top_contrib_row = self.db.execute(
            select(Commit.author_login, Commit.author_name, func.count(Commit.id).label("c_count"))
            .join(Repository)
            .where(Repository.user_id == user_id)
            .group_by(Commit.author_login, Commit.author_name)
            .order_by(func.count(Commit.id).desc())
            .limit(1)
        ).first()
        top_contributor = {
            "login": top_contrib_row.author_login or top_contrib_row.author_name if top_contrib_row else "N/A",
            "count": top_contrib_row.c_count if top_contrib_row else 0
        }

        # 4. Weekly Trend (commits per day in last 7 days)
        last_7_days_rows = self.db.execute(
            select(func.date(Commit.committed_at).label("date"), func.count(Commit.id).label("count"))
            .join(Repository)
            .where(Repository.user_id == user_id, Commit.committed_at >= seven_days_ago)
            .group_by(func.date(Commit.committed_at))
            .order_by(func.date(Commit.committed_at))
        ).all()
        last_7_days_map = {str(row.date): row.count for row in last_7_days_rows}
        weekly_trend = []
        for i in range(7):
            d = (datetime.now(UTC) - timedelta(days=6-i)).date()
            ds = str(d)
            weekly_trend.append({"date": ds, "count": last_7_days_map.get(ds, 0)})

        # 5. Commit Distribution by day of week (last 30 days)
        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
        recent_commits_dates = self.db.scalars(
            select(Commit.committed_at)
            .join(Repository)
            .where(Repository.user_id == user_id, Commit.committed_at >= thirty_days_ago)
        ).all()
        day_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
        day_counts = [0] * 7
        for dt in recent_commits_dates:
            day_counts[dt.weekday()] += 1
        commit_dist_by_day = [{"day": day_names[i], "count": day_counts[i]} for i in range(7)]

        advanced = self._build_global_advanced_analytics(user_id, repos, repo_ids)

        return {
            "summary": {
                "total_repositories": total_repos,
                "synced_repositories": synced_repos,
                "private_repositories": private_repos,
                "public_repositories": public_repos,
                "total_commits": total_commits,
                "total_prs": total_prs,
                "total_issues": total_issues,
                "total_contributors": total_contributors,
                "active_repositories": active_repos_count,
                "inactive_repositories": inactive_repos_count,
                "commits_last_7_days": commits_last_7,
                "top_contributor": top_contributor,
                "most_active_repository": most_active[0] if most_active else {"full_name": "N/A", "commit_count": 0},
            },
            "most_active_repositories": most_active,
            "latest_sync_activity": latest_syncs,
            "charts": {
                "global_commits_per_day": global_commits_per_day,
                "private_public_ratio": {
                    "private": private_repos,
                    "public": public_repos,
                },
                "commit_dist_by_day": commit_dist_by_day,
                "weekly_trend": weekly_trend,
                "active_inactive_ratio": {
                    "active": active_repos_count,
                    "inactive": inactive_repos_count,
                }
            },
            "health": advanced["health"],
            "heatmap": advanced["heatmap"],
            "insights": advanced["insights"],
            "team": advanced["team"],
            "kpi": advanced["kpi"],
            "kpi_charts": advanced["kpi_charts"],
            "activity_timeline": advanced["activity_timeline"],
        }

    def _build_global_advanced_analytics(
        self,
        user_id: int,
        repos: list[Repository],
        repo_ids: list[int],
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        if not repo_ids:
            return {
                "health": _empty_health_score(),
                "heatmap": _empty_heatmap(now.date()),
                "insights": [],
                "team": _empty_team_dashboard(),
                "kpi": _empty_kpi_rankings(),
                "kpi_charts": _empty_kpi_charts(),
                "activity_timeline": [],
            }

        since_7 = now - timedelta(days=7)
        prev_7_start = now - timedelta(days=14)
        since_30 = now - timedelta(days=30)
        since_90 = now - timedelta(days=90)
        since_365 = now - timedelta(days=364)

        commits_recent = self.db.scalars(
            select(Commit)
            .join(Repository)
            .where(Repository.user_id == user_id, Commit.committed_at >= since_90)
            .order_by(Commit.committed_at.desc())
        ).all()
        commits_year = self.db.execute(
            select(
                func.date(Commit.committed_at).label("day"),
                func.count(Commit.id).label("count"),
            )
            .join(Repository)
            .where(Repository.user_id == user_id, Commit.committed_at >= since_365)
            .group_by(func.date(Commit.committed_at))
            .order_by(func.date(Commit.committed_at))
        ).all()
        prs = self.db.scalars(
            select(PullRequest)
            .join(Repository)
            .where(Repository.user_id == user_id)
        ).all()
        issues = self.db.scalars(
            select(Issue)
            .join(Repository)
            .where(Repository.user_id == user_id)
        ).all()

        health = self._calculate_health_score(
            repos=repos,
            commits=commits_recent,
            pull_requests=prs,
            issues=issues,
            now=now,
            since_7=since_7,
            prev_7_start=prev_7_start,
        )
        heatmap = self._build_commit_heatmap(commits_year, now.date())
        insights = self._build_rule_based_insights(
            commits=commits_recent,
            pull_requests=prs,
            issues=issues,
            health=health,
            now=now,
            since_7=since_7,
            prev_7_start=prev_7_start,
        )
        team = self._build_team_dashboard(commits_recent, prs, issues)
        kpi = self._build_kpi_rankings(repos, commits_recent, prs, issues, team)
        kpi_charts = self._build_kpi_charts(repos, commits_recent, team)
        activity_timeline = self._build_activity_timeline(repos, commits_recent, prs, issues)

        return {
            "health": health,
            "heatmap": heatmap,
            "insights": insights,
            "team": team,
            "kpi": kpi,
            "kpi_charts": kpi_charts,
            "activity_timeline": activity_timeline,
        }

    def _calculate_health_score(
        self,
        *,
        repos: list[Repository],
        commits: list[Commit],
        pull_requests: list[PullRequest],
        issues: list[Issue],
        now: datetime,
        since_7: datetime,
        prev_7_start: datetime,
    ) -> dict[str, Any]:
        commits_7 = [c for c in commits if _ensure_aware(c.committed_at) >= since_7]
        commits_prev = [
            c for c in commits
            if prev_7_start <= _ensure_aware(c.committed_at) < since_7
        ]
        closed_issues = [i for i in issues if i.closed_at is not None or i.state == "closed"]
        open_issues = [i for i in issues if i.state == "open"]
        stale_issues = [
            i for i in open_issues
            if _ensure_aware(i.updated_at or i.created_at) < now - timedelta(days=30)
        ]
        merged_prs = [p for p in pull_requests if p.is_merged and p.merged_at and p.created_at]
        active_contributors = {
            c.author_login or c.author_email or c.author_name
            for c in commits
            if _ensure_aware(c.committed_at) >= now - timedelta(days=30)
        }
        latest_commit = max((_ensure_aware(c.committed_at) for c in commits), default=None)
        latest_sync = max((_ensure_aware(r.last_synced_at) for r in repos if r.last_synced_at), default=None)
        latest_activity = latest_commit or latest_sync
        if latest_commit and latest_sync:
            latest_activity = max(latest_commit, latest_sync)
        inactive_days = (now - latest_activity).days if latest_activity else 999

        avg_merge_hours = None
        if merged_prs:
            merge_hours = [
                (_ensure_aware(pr.merged_at) - _ensure_aware(pr.created_at)).total_seconds() / 3600
                for pr in merged_prs
            ]
            avg_merge_hours = round(sum(merge_hours) / len(merge_hours), 1)

        issue_resolution_ratio = _percent(len(closed_issues), len(issues))
        stale_ratio = _percent(len(stale_issues), len(open_issues))
        commit_frequency_score = min(100, int((len(commits_7) / max(1, len(repos))) * 20))
        issue_score = int(issue_resolution_ratio)
        pr_speed_score = 100 if avg_merge_hours is None else max(0, min(100, int(100 - (avg_merge_hours / 72) * 45)))
        contributor_score = min(100, int((len(active_contributors) / max(1, len(repos))) * 65))
        stale_score = max(0, int(100 - stale_ratio))
        inactive_score = max(0, min(100, int(100 - inactive_days * 4)))

        score = round(
            commit_frequency_score * 0.24
            + issue_score * 0.19
            + pr_speed_score * 0.18
            + contributor_score * 0.17
            + stale_score * 0.12
            + inactive_score * 0.10
        )
        status = _health_status(score)
        activity_delta = _percent_delta(len(commits_7), len(commits_prev))
        recommendation = _health_recommendation(
            score=score,
            inactive_days=inactive_days,
            stale_ratio=stale_ratio,
            avg_merge_hours=avg_merge_hours,
            commits_7=len(commits_7),
        )

        return {
            "score": score,
            "status": status,
            "recommendation": recommendation,
            "primary_insight": _activity_delta_sentence(activity_delta),
            "metrics": {
                "commit_frequency": commit_frequency_score,
                "issue_resolution": issue_score,
                "pr_merge_speed": pr_speed_score,
                "contributor_activity": contributor_score,
                "stale_issue_ratio": stale_score,
                "inactive_days": inactive_score,
            },
            "raw": {
                "commits_last_7_days": len(commits_7),
                "previous_7_day_commits": len(commits_prev),
                "activity_delta_percent": activity_delta,
                "closed_issues": len(closed_issues),
                "open_issues": len(open_issues),
                "stale_issues": len(stale_issues),
                "stale_issue_ratio": round(stale_ratio, 1),
                "avg_pr_merge_hours": avg_merge_hours,
                "active_contributors": len(active_contributors),
                "inactive_days": inactive_days if inactive_days != 999 else None,
            },
            "breakdown": [
                {"label": "Nhịp commit", "value": commit_frequency_score},
                {"label": "Xử lý issue", "value": issue_score},
                {"label": "Tốc độ merge PR", "value": pr_speed_score},
                {"label": "Hoạt động contributor", "value": contributor_score},
                {"label": "Issue tồn đọng", "value": stale_score},
                {"label": "Hoạt động gần đây", "value": inactive_score},
            ],
        }

    def _build_commit_heatmap(self, rows: list[Any], today: date) -> dict[str, Any]:
        counts_by_day = {str(row.day): int(row.count) for row in rows}
        days = []
        max_count = max(counts_by_day.values(), default=0)
        start = today - timedelta(days=364)
        for offset in range(365):
            current = start + timedelta(days=offset)
            count = counts_by_day.get(current.isoformat(), 0)
            days.append(
                {
                    "date": current.isoformat(),
                    "count": count,
                    "level": _heatmap_level(count, max_count),
                    "label": f"{count} commit vào {current.strftime('%d/%m')}",
                }
            )
        return {
            "days": days,
            "max_count": max_count,
            "total_commits": sum(counts_by_day.values()),
        }

    def _build_rule_based_insights(
        self,
        *,
        commits: list[Commit],
        pull_requests: list[PullRequest],
        issues: list[Issue],
        health: dict[str, Any],
        now: datetime,
        since_7: datetime,
        prev_7_start: datetime,
    ) -> list[dict[str, Any]]:
        insights: list[dict[str, Any]] = []
        commits_7 = [c for c in commits if _ensure_aware(c.committed_at) >= since_7]
        commits_prev = [
            c for c in commits
            if prev_7_start <= _ensure_aware(c.committed_at) < since_7
        ]
        delta = _percent_delta(len(commits_7), len(commits_prev))

        if commits:
            weekday_counts: dict[int, int] = defaultdict(int)
            hour_counts: dict[int, int] = defaultdict(int)
            for commit in commits:
                committed_at = _ensure_aware(commit.committed_at)
                weekday_counts[committed_at.weekday()] += 1
                hour_counts[committed_at.hour] += 1
            best_day = max(weekday_counts.items(), key=lambda item: item[1])
            best_hour = max(hour_counts.items(), key=lambda item: item[1])
            insights.append(
                {
                    "title": "Ngày coding hiệu quả nhất",
                    "value": _weekday_name(best_day[0]),
                    "detail": f"{best_day[1]} commit tập trung vào {_weekday_name(best_day[0])}.",
                    "tone": "positive",
                    "icon": "calendar",
                }
            )
            insights.append(
                {
                    "title": "Khung giờ hoạt động cao",
                    "value": _hour_bucket(best_hour[0]),
                    "detail": f"Hoạt động nổi bật quanh {_hour_bucket(best_hour[0])}.",
                    "tone": "info",
                    "icon": "clock",
                }
            )
            insights.append(
                {
                    "title": "Độ đều commit",
                    "value": f"{len({c.committed_at.date() for c in commits_7})}/7 ngày",
                    "detail": _activity_delta_sentence(delta),
                    "tone": "positive" if delta >= 0 else "warning",
                    "icon": "activity",
                }
            )

        merged_prs = [p for p in pull_requests if p.is_merged and p.merged_at and p.created_at]
        if merged_prs:
            avg_hours = sum(
                (_ensure_aware(p.merged_at) - _ensure_aware(p.created_at)).total_seconds() / 3600
                for p in merged_prs
            ) / len(merged_prs)
            insights.append(
                {
                    "title": "Hiệu suất merge PR",
                    "value": f"{round(avg_hours, 1)}h",
                    "detail": "Thời gian merge đang tốt." if avg_hours <= 48 else "Vòng review đang chậm lại.",
                    "tone": "positive" if avg_hours <= 48 else "warning",
                    "icon": "git-pull-request",
                }
            )

        closed_issues_recent = [
            i for i in issues
            if i.closed_at and _ensure_aware(i.closed_at) >= now - timedelta(days=30)
        ]
        open_issues = [i for i in issues if i.state == "open"]
        if issues:
            insights.append(
                {
                    "title": "Xu hướng xử lý issue",
                    "value": f"{len(closed_issues_recent)} đã xử lý",
                    "detail": f"Còn {len(open_issues)} issue đang mở trong các repository đã sync.",
                    "tone": "positive" if len(closed_issues_recent) >= len(open_issues) else "info",
                    "icon": "circle-check",
                }
            )

        insights.append(
            {
                "title": "Xu hướng năng suất",
                "value": f"{delta:+.0f}%",
                "detail": _activity_delta_sentence(delta),
                "tone": "positive" if delta >= 0 else "warning",
                "icon": "trending-up",
            }
        )
        insights.append(
            {
                "title": "Sức khỏe repository",
                "value": health["status"]["label"],
                "detail": health["recommendation"],
                "tone": health["status"]["tone"],
                "icon": "shield",
            }
        )
        return insights[:6]

    def _build_team_dashboard(
        self,
        commits: list[Commit],
        pull_requests: list[PullRequest],
        issues: list[Issue],
    ) -> dict[str, Any]:
        people: dict[str, dict[str, Any]] = {}

        def person(key: str | None, name: str | None = None, avatar_url: str | None = None) -> dict[str, Any]:
            identity = key or name or "Unknown"
            if identity not in people:
                people[identity] = {
                    "name": name or identity,
                    "login": key,
                    "avatar_url": avatar_url,
                    "commits": 0,
                    "issues_closed": 0,
                    "prs_merged": 0,
                    "active_days": set(),
                    "score": 0,
                }
            if avatar_url and not people[identity]["avatar_url"]:
                people[identity]["avatar_url"] = avatar_url
            return people[identity]

        for commit in commits:
            item = person(commit.author_login, commit.author_name, commit.author_avatar_url)
            item["commits"] += 1
            item["active_days"].add(_ensure_aware(commit.committed_at).date().isoformat())

        for pr in pull_requests:
            item = person(pr.author_login, pr.author_login, pr.author_avatar_url)
            if pr.is_merged:
                item["prs_merged"] += 1

        for issue in issues:
            item = person(issue.author_login, issue.author_login, issue.author_avatar_url)
            if issue.state == "closed" or issue.closed_at is not None:
                item["issues_closed"] += 1

        leaderboard = []
        for item in people.values():
            active_days = len(item["active_days"])
            score = item["commits"] + item["prs_merged"] * 3 + item["issues_closed"] * 2 + active_days
            leaderboard.append(
                {
                    "name": item["name"],
                    "login": item["login"],
                    "avatar_url": item["avatar_url"],
                    "commits": item["commits"],
                    "issues_closed": item["issues_closed"],
                    "prs_merged": item["prs_merged"],
                    "active_days": active_days,
                    "score": score,
                }
            )
        leaderboard.sort(key=lambda row: row["score"], reverse=True)

        return {
            "leaderboard": leaderboard[:10],
            "members": leaderboard,
            "top_contributors": sorted(leaderboard, key=lambda row: row["commits"], reverse=True)[:6],
            "issue_resolvers": sorted(leaderboard, key=lambda row: row["issues_closed"], reverse=True)[:6],
            "pr_activity": sorted(leaderboard, key=lambda row: row["prs_merged"], reverse=True)[:6],
            "summary": {
                "contributors": len(leaderboard),
                "active_days": len({day for item in people.values() for day in item["active_days"]}),
                "commits": sum(item["commits"] for item in people.values()),
                "issues_closed": sum(item["issues_closed"] for item in people.values()),
                "prs_merged": sum(item["prs_merged"] for item in people.values()),
            },
        }

    def _build_kpi_rankings(
        self,
        repos: list[Repository],
        commits: list[Commit],
        pull_requests: list[PullRequest],
        issues: list[Issue],
        team: dict[str, Any],
    ) -> dict[str, Any]:
        leaderboard = team.get("leaderboard", [])
        top_contributor = max(leaderboard, key=lambda row: row["commits"], default=None)
        top_issue_resolver = max(leaderboard, key=lambda row: row["issues_closed"], default=None)

        merged_prs = [pr for pr in pull_requests if pr.is_merged and pr.merged_at and pr.created_at]
        fastest_pr = min(
            merged_prs,
            key=lambda pr: (_ensure_aware(pr.merged_at) - _ensure_aware(pr.created_at)).total_seconds(),
            default=None,
        )
        fastest_reviewer = None
        if fastest_pr:
            merge_hours = round(
                (_ensure_aware(fastest_pr.merged_at) - _ensure_aware(fastest_pr.created_at)).total_seconds() / 3600,
                1,
            )
            fastest_reviewer = {
                "name": fastest_pr.author_login,
                "login": fastest_pr.author_login,
                "value": f"{merge_hours}h",
                "detail": f"PR #{fastest_pr.number} merged fastest",
            }

        commit_count_by_repo: dict[int, int] = defaultdict(int)
        issue_closed_by_repo: dict[int, int] = defaultdict(int)
        pr_merged_by_repo: dict[int, int] = defaultdict(int)
        for commit in commits:
            commit_count_by_repo[commit.repo_id] += 1
        for issue in issues:
            if issue.state == "closed" or issue.closed_at:
                issue_closed_by_repo[issue.repo_id] += 1
        for pr in pull_requests:
            if pr.is_merged:
                pr_merged_by_repo[pr.repo_id] += 1

        repo_scores = []
        for repo in repos:
            commits_count = commit_count_by_repo.get(repo.id, 0)
            issues_count = issue_closed_by_repo.get(repo.id, 0)
            prs_count = pr_merged_by_repo.get(repo.id, 0)
            score = commits_count + prs_count * 3 + issues_count * 2
            repo_scores.append(
                {
                    "id": repo.id,
                    "full_name": repo.full_name,
                    "commits": commits_count,
                    "issues_closed": issues_count,
                    "prs_merged": prs_count,
                    "score": score,
                }
            )
        most_active_repo = max(repo_scores, key=lambda row: row["score"], default=None)

        return {
            "top_contributor": _kpi_person(top_contributor, "commits"),
            "top_issue_resolver": _kpi_person(top_issue_resolver, "issues_closed"),
            "fastest_reviewer": fastest_reviewer or {"name": "N/A", "value": "N/A", "detail": "No merged pull requests yet"},
            "most_active_repo": most_active_repo or {"full_name": "N/A", "score": 0, "commits": 0, "issues_closed": 0, "prs_merged": 0},
        }

    def _build_kpi_charts(
        self,
        repos: list[Repository],
        commits: list[Commit],
        team: dict[str, Any],
    ) -> dict[str, Any]:
        members = team.get("members", [])
        commits_by_repo: dict[int, int] = defaultdict(int)
        for commit in commits:
            commits_by_repo[commit.repo_id] += 1
        repo_rows = sorted(
            [
                {
                    "repo": repo.full_name,
                    "commits": commits_by_repo.get(repo.id, 0),
                }
                for repo in repos
            ],
            key=lambda row: row["commits"],
            reverse=True,
        )
        # Repo commit counts are already available through most_active_repositories on the overview.
        return {
            "commits_by_contributor": [
                {"label": row["login"] or row["name"], "value": row["commits"]}
                for row in sorted(members, key=lambda row: row["commits"], reverse=True)[:8]
            ],
            "issues_resolved_by_user": [
                {"label": row["login"] or row["name"], "value": row["issues_closed"]}
                for row in sorted(members, key=lambda row: row["issues_closed"], reverse=True)[:8]
            ],
            "commits_per_repo": repo_rows[:8],
        }

    def _build_activity_timeline(
        self,
        repos: list[Repository],
        commits: list[Commit],
        pull_requests: list[PullRequest],
        issues: list[Issue],
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        repo_names = {repo.id: repo.full_name for repo in repos}
        for repo in repos:
            if repo.last_synced_at:
                events.append(
                    {
                        "type": "sync",
                        "label": "Đồng bộ hoàn tất" if repo.last_sync_status == "success" else "Đã cập nhật đồng bộ",
                        "repo": repo.full_name,
                        "timestamp": _vn_iso(repo.last_synced_at),
                        "badge": repo.last_sync_status,
                    }
                )
            if repo.created_at:
                events.append(
                    {
                        "type": "repository",
                        "label": "Đã import repository",
                        "repo": repo.full_name,
                        "timestamp": _vn_iso(repo.created_at),
                        "badge": "imported",
                    }
                )

        for commit in commits[:15]:
            events.append(
                {
                    "type": "commit",
                    "label": "Commit mới",
                    "repo": repo_names.get(commit.repo_id, "Repository"),
                    "detail": (commit.message or "").splitlines()[0][:90],
                    "timestamp": _vn_iso(commit.committed_at),
                    "badge": "commit",
                }
            )
        for pr in pull_requests:
            if pr.is_merged and pr.merged_at:
                events.append(
                    {
                        "type": "pull_request",
                        "label": "PR đã merge",
                        "repo": repo_names.get(pr.repo_id, "Repository"),
                        "detail": f"#{pr.number} {pr.title[:80]}",
                        "timestamp": _vn_iso(pr.merged_at),
                        "badge": "merged",
                    }
                )
        for issue in issues:
            if issue.closed_at:
                events.append(
                    {
                        "type": "issue",
                        "label": "Issue đã xử lý",
                        "repo": repo_names.get(issue.repo_id, "Repository"),
                        "detail": f"#{issue.number} {issue.title[:80]}",
                        "timestamp": _vn_iso(issue.closed_at),
                        "badge": "closed",
                    }
                )

        events.sort(key=lambda row: row["timestamp"], reverse=True)
        return events[:24]

    def _get_repo(self, user_id: int, repo_id: int):
        repo = self.repo_repo.get_by_user_and_id(user_id, repo_id)
        if repo is None:
            raise RepositoryNotFoundException("Repository not found.")
        return repo

    # ── Overview ─────────────────────────────────────────────────────────────

    def get_branch_options(self, user_id: int, repo_id: int) -> dict[str, Any]:
        repo = self._get_repo(user_id, repo_id)
        branches = self.db.scalars(
            select(Branch)
            .where(Branch.repository_id == repo_id)
            .order_by(Branch.is_default.desc(), Branch.github_branch_name.asc())
        ).all()
        names = [branch.github_branch_name for branch in branches]
        if not names and repo.default_branch:
            names = [repo.default_branch]
        patterns = ["feature/*", "release/*"]
        return {
            "selected": "all",
            "options": [
                {"label": "Tất cả branch", "value": "all"},
                *[
                    {
                        "label": name,
                        "value": name,
                        "is_default": name == repo.default_branch,
                    }
                    for name in names
                ],
                *[{"label": pattern, "value": pattern, "is_pattern": True} for pattern in patterns],
            ],
        }

    def get_overview(
        self,
        user_id: int,
        repo_id: int,
        branch_filter: str | None = None,
    ) -> dict[str, Any]:
        repo = self._get_repo(user_id, repo_id)

        commits_per_day = self.commit_repo.commits_per_day(repo_id, branch_filter)
        total_commits = sum(day["count"] for day in commits_per_day)
        pr_summary = self.pr_repo.pr_status_summary(repo_id, branch_filter)
        issue_state = self.issue_repo.issues_by_state(repo_id)
        contributors = self.contributor_repo.list_by_repo(repo_id, page=1, per_page=100)

        recent_commits = self.commit_repo.list_by_repo(
            repo_id,
            page=1,
            per_page=5,
            branch_filter=branch_filter,
        )
        recent_prs = self.pr_repo.list_by_repo(
            repo_id,
            page=1,
            per_page=5,
            branch_filter=branch_filter,
        )
        recent_issues = self.issue_repo.list_by_repo(repo_id, page=1, per_page=5)

        active_days = len(commits_per_day)

        return {
            "repository": {
                "id": repo.id,
                "full_name": repo.full_name,
                "html_url": repo.html_url,
                "default_branch": repo.default_branch,
                "last_synced_at": _vn_iso(repo.last_synced_at),
                "last_sync_status": repo.last_sync_status,
            },
            "branch_filter": {
                **self.get_branch_options(user_id, repo_id),
                "selected": branch_filter or "all",
            },
            "summary": {
                "total_commits": total_commits,
                "active_days": active_days,
                "total_prs": sum(pr_summary.values()),
                "open_prs": pr_summary.get("open", 0),
                "merged_prs": pr_summary.get("merged", 0),
                "closed_prs": pr_summary.get("closed", 0),
                "open_issues": issue_state.get("open", 0),
                "closed_issues": issue_state.get("closed", 0),
                "total_contributors": len(contributors),
            },
            "charts": {
                "commits_per_day": commits_per_day[-30:],  # last 30 data points
                "pr_status": pr_summary,
                "issue_status": {
                    "open": issue_state.get("open", 0),
                    "closed": issue_state.get("closed", 0),
                },
            },
            "recent": {
                "commits": [_fmt_commit(c) for c in recent_commits],
                "pull_requests": [_fmt_pr(p) for p in recent_prs],
                "issues": [_fmt_issue(i) for i in recent_issues],
            },
        }

    # ── Commits ───────────────────────────────────────────────────────────────

    def get_commits(
        self,
        user_id: int,
        repo_id: int,
        branch_filter: str | None = None,
    ) -> dict[str, Any]:
        self._get_repo(user_id, repo_id)

        commits_per_day = self.commit_repo.commits_per_day(repo_id, branch_filter)
        by_contributor = self.commit_repo.commits_by_contributor(repo_id, branch_filter)
        recent = self.commit_repo.list_by_repo(
            repo_id,
            page=1,
            per_page=20,
            branch_filter=branch_filter,
        )

        active_days = len([d for d in commits_per_day if d["count"] > 0])
        total = sum(d["count"] for d in commits_per_day)

        return {
            "summary": {
                "total": total,
                "active_days": active_days,
            },
            "branch_filter": {
                **self.get_branch_options(user_id, repo_id),
                "selected": branch_filter or "all",
            },
            "charts": {
                "per_day": commits_per_day,
                "by_contributor": by_contributor[:15],
            },
            "recent": [_fmt_commit(c) for c in recent],
        }

    # ── Pull Requests ─────────────────────────────────────────────────────────

    def get_pull_requests(
        self,
        user_id: int,
        repo_id: int,
        branch_filter: str | None = None,
    ) -> dict[str, Any]:
        self._get_repo(user_id, repo_id)

        summary = self.pr_repo.pr_status_summary(repo_id, branch_filter)
        recent = self.pr_repo.list_by_repo(
            repo_id,
            page=1,
            per_page=20,
            branch_filter=branch_filter,
        )

        # average merge time (hours) from recent set
        merge_times = []
        for pr in recent:
            if pr.merged_at and pr.created_at:
                delta = pr.merged_at - pr.created_at
                merge_times.append(delta.total_seconds() / 3600)
        avg_merge_hours = round(sum(merge_times) / len(merge_times), 1) if merge_times else None

        return {
            "summary": {
                "total": sum(summary.values()),
                "open": summary.get("open", 0),
                "merged": summary.get("merged", 0),
                "closed": summary.get("closed", 0),
                "avg_merge_time_hours": avg_merge_hours,
            },
            "branch_filter": {
                **self.get_branch_options(user_id, repo_id),
                "selected": branch_filter or "all",
            },
            "charts": {
                "status": summary,
            },
            "recent": [_fmt_pr(p) for p in recent],
        }

    # ── Issues ────────────────────────────────────────────────────────────────

    def get_issues(
        self,
        user_id: int,
        repo_id: int,
        branch_filter: str | None = None,
    ) -> dict[str, Any]:
        self._get_repo(user_id, repo_id)

        by_state = self.issue_repo.issues_by_state(repo_id)
        recent = self.issue_repo.list_by_repo(repo_id, page=1, per_page=20)

        # label frequency
        label_counts: dict[str, int] = {}
        for issue in recent:
            for label in (issue.labels or []):
                label_counts[label] = label_counts.get(label, 0) + 1

        # average close time (hours)
        close_times = []
        for issue in recent:
            if issue.closed_at and issue.created_at:
                delta = issue.closed_at - issue.created_at
                close_times.append(delta.total_seconds() / 3600)
        avg_close_hours = round(sum(close_times) / len(close_times), 1) if close_times else None

        return {
            "summary": {
                "total": sum(by_state.values()),
                "open": by_state.get("open", 0),
                "closed": by_state.get("closed", 0),
                "avg_close_time_hours": avg_close_hours,
            },
            "branch_filter": {
                **self.get_branch_options(user_id, repo_id),
                "selected": branch_filter or "all",
            },
            "charts": {
                "by_state": by_state,
                "by_label": sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            },
            "recent": [_fmt_issue(i) for i in recent],
        }

    # ── Contributors ──────────────────────────────────────────────────────────

    def get_contributors(
        self,
        user_id: int,
        repo_id: int,
        branch_filter: str | None = None,
    ) -> dict[str, Any]:
        self._get_repo(user_id, repo_id)

        by_commits = self.commit_repo.commits_by_contributor(repo_id, branch_filter)

        return {
            "summary": {
                "total": len(by_commits),
            },
            "branch_filter": {
                **self.get_branch_options(user_id, repo_id),
                "selected": branch_filter or "all",
            },
            "top_contributors": by_commits[:20],
        }

    def get_contributor_profile(self, user_id: int, username: str) -> dict[str, Any]:
        normalized = username.strip()
        if not normalized:
            raise RepositoryNotFoundException("Contributor not found.")

        repos = self.repo_repo.list_by_user(user_id, page=1, per_page=100)
        repo_ids = [repo.id for repo in repos]
        if not repo_ids:
            raise RepositoryNotFoundException("Contributor not found.")

        commits = self.db.scalars(
            select(Commit)
            .join(Repository)
            .where(
                Repository.user_id == user_id,
                Commit.author_login == normalized,
            )
            .order_by(Commit.committed_at.desc())
        ).all()
        prs = self.db.scalars(
            select(PullRequest)
            .join(Repository)
            .where(
                Repository.user_id == user_id,
                PullRequest.author_login == normalized,
            )
            .order_by(PullRequest.created_at.desc())
        ).all()
        issues = self.db.scalars(
            select(Issue)
            .join(Repository)
            .where(
                Repository.user_id == user_id,
                Issue.author_login == normalized,
            )
            .order_by(Issue.created_at.desc())
        ).all()

        if not commits and not prs and not issues:
            raise RepositoryNotFoundException("Contributor not found.")

        repo_names = {repo.id: repo.full_name for repo in repos}
        repo_languages = {repo.id: repo.language for repo in repos if repo.language}
        avatar_url = next((c.author_avatar_url for c in commits if c.author_avatar_url), None)
        display_name = next((c.author_name for c in commits if c.author_name), normalized)

        now = datetime.now(UTC)
        since_30 = now - timedelta(days=30)
        since_7 = now - timedelta(days=7)
        commits_30 = [c for c in commits if _ensure_aware(c.committed_at) >= since_30]
        commits_7 = [c for c in commits if _ensure_aware(c.committed_at) >= since_7]
        active_days = sorted({_ensure_aware(c.committed_at).date() for c in commits})
        current_streak, longest_streak = _date_streaks(active_days, now.date())

        commits_by_day: dict[str, int] = defaultdict(int)
        commits_by_week: dict[str, int] = defaultdict(int)
        hour_counts = {hour: 0 for hour in range(24)}
        weekday_hour: dict[str, list[int]] = {
            name: [0] * 24 for name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        }
        repo_counts: dict[int, int] = defaultdict(int)
        language_counts: dict[str, int] = defaultdict(int)

        for commit in commits:
            committed_at = _ensure_aware(commit.committed_at)
            day_key = committed_at.date().isoformat()
            week_key = f"{committed_at.isocalendar().year}-W{committed_at.isocalendar().week:02d}"
            commits_by_day[day_key] += 1
            commits_by_week[week_key] += 1
            hour_counts[committed_at.hour] += 1
            weekday_hour[_weekday_name(committed_at.weekday())[:3]][committed_at.hour] += 1
            repo_counts[commit.repo_id] += 1
            language = repo_languages.get(commit.repo_id)
            if language:
                language_counts[language] += 1

        merged_prs = [pr for pr in prs if pr.is_merged]
        resolved_issues = [issue for issue in issues if issue.state == "closed" or issue.closed_at]
        participation = len(repo_counts)
        score = min(
            100,
            len(commits_30) * 2
            + len(merged_prs) * 5
            + len(resolved_issues) * 4
            + current_streak * 3
            + participation * 4,
        )
        peak_hour = max(hour_counts.items(), key=lambda item: item[1])[0] if commits else None

        top_repositories = [
            {
                "id": repo_id,
                "full_name": repo_names.get(repo_id, "Repository"),
                "commits": count,
                "language": repo_languages.get(repo_id),
            }
            for repo_id, count in sorted(repo_counts.items(), key=lambda item: item[1], reverse=True)[:8]
        ]
        weeks = [
            {"week": week, "count": commits_by_week[week]}
            for week in sorted(commits_by_week)[-12:]
        ]
        trend = [
            {
                "date": (now.date() - timedelta(days=offset)).isoformat(),
                "count": commits_by_day.get((now.date() - timedelta(days=offset)).isoformat(), 0),
            }
            for offset in range(29, -1, -1)
        ]

        leaderboards = self._build_contributor_leaderboards(user_id)

        return {
            "profile": {
                "username": normalized,
                "display_name": display_name,
                "avatar_url": avatar_url,
                "github_url": f"https://github.com/{normalized}",
                "score": score,
                "current_streak": current_streak,
                "longest_streak": longest_streak,
                "primary_languages": [
                    {"name": language, "count": count}
                    for language, count in sorted(
                        language_counts.items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )[:4]
                ],
            },
            "summary": {
                "commits": len(commits),
                "commits_7d": len(commits_7),
                "commits_30d": len(commits_30),
                "prs_merged": len(merged_prs),
                "issues_resolved": len(resolved_issues),
                "active_days": len(active_days),
                "repositories": participation,
                "peak_hour": peak_hour,
            },
            "charts": {
                "contribution_trend": trend,
                "commits_per_week": weeks,
                "active_hours": [{"hour": hour, "count": count} for hour, count in hour_counts.items()],
                "hour_heatmap": [
                    {"day": day, "hours": counts}
                    for day, counts in weekday_hour.items()
                ],
                "top_repositories": top_repositories,
            },
            "insights": _contributor_insights(
                commits=commits,
                commits_30=len(commits_30),
                current_streak=current_streak,
                participation=participation,
                peak_hour=peak_hour,
            ),
            "leaderboards": leaderboards,
        }

    def _build_contributor_leaderboards(self, user_id: int) -> dict[str, list[dict[str, Any]]]:
        since_7 = datetime.now(UTC) - timedelta(days=7)
        top_contributors = self.db.execute(
            select(
                Commit.author_login.label("login"),
                Commit.author_name.label("name"),
                Commit.author_avatar_url.label("avatar_url"),
                func.count(Commit.id).label("count"),
            )
            .join(Repository)
            .where(Repository.user_id == user_id, Commit.author_login.is_not(None))
            .group_by(Commit.author_login, Commit.author_name, Commit.author_avatar_url)
            .order_by(func.count(Commit.id).desc())
            .limit(5)
        ).all()
        active_week = self.db.execute(
            select(
                Commit.author_login.label("login"),
                Commit.author_name.label("name"),
                Commit.author_avatar_url.label("avatar_url"),
                func.count(Commit.id).label("count"),
            )
            .join(Repository)
            .where(
                Repository.user_id == user_id,
                Commit.author_login.is_not(None),
                Commit.committed_at >= since_7,
            )
            .group_by(Commit.author_login, Commit.author_name, Commit.author_avatar_url)
            .order_by(func.count(Commit.id).desc())
            .limit(5)
        ).all()
        issue_resolvers = self.db.execute(
            select(
                Issue.author_login.label("login"),
                func.count(Issue.id).label("count"),
            )
            .join(Repository)
            .where(
                Repository.user_id == user_id,
                Issue.author_login.is_not(None),
                Issue.state == "closed",
            )
            .group_by(Issue.author_login)
            .order_by(func.count(Issue.id).desc())
            .limit(5)
        ).all()

        def rows(items: list[Any]) -> list[dict[str, Any]]:
            return [
                {
                    "login": row.login,
                    "name": getattr(row, "name", None) or row.login,
                    "avatar_url": getattr(row, "avatar_url", None),
                    "count": row.count,
                }
                for row in items
            ]

        return {
            "top_contributor": rows(top_contributors),
            "most_active_week": rows(active_week),
            "issue_resolver": rows(issue_resolvers),
        }


# ── Formatters ────────────────────────────────────────────────────────────────

def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _percent(part: int, total: int) -> float:
    if total <= 0:
        return 100.0
    return round((part / total) * 100, 1)


def _percent_delta(current: int, previous: int) -> float:
    if previous <= 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def _health_status(score: int) -> dict[str, str]:
    if score >= 85:
        return {"label": "Rất tốt", "tone": "positive"}
    if score >= 70:
        return {"label": "Ổn định", "tone": "positive"}
    if score >= 45:
        return {"label": "Cần chú ý", "tone": "warning"}
    return {"label": "Rủi ro cao", "tone": "critical"}


def _health_recommendation(
    *,
    score: int,
    inactive_days: int,
    stale_ratio: float,
    avg_merge_hours: float | None,
    commits_7: int,
) -> str:
    if commits_7 == 0:
        return "Tuần này chưa ghi nhận commit mới. Nên kiểm tra lịch sync hoặc quyền sở hữu repository."
    if inactive_days >= 14:
        return f"Repository chưa có hoạt động trong {inactive_days} ngày."
    if stale_ratio >= 40:
        return "Tỷ lệ issue tồn đọng cao. Nên ưu tiên triage và đóng các issue đã cũ."
    if avg_merge_hours is not None and avg_merge_hours >= 72:
        return "Tốc độ merge PR đang chậm. Nên giảm backlog review và chia PR nhỏ hơn."
    if score >= 85:
        return "Tín hiệu repository đang tốt ở activity, review speed và issue flow."
    return "Hoạt động ổn định. Giữ nhịp commit và xử lý issue cân bằng."


def _activity_delta_sentence(delta: float) -> str:
    if delta > 0:
        return f"Hoạt động repository tăng {abs(delta):.0f}% trong tuần này."
    if delta < 0:
        return f"Hoạt động repository giảm {abs(delta):.0f}% trong tuần này."
    return "Hoạt động repository ổn định trong tuần này."


def _heatmap_level(count: int, max_count: int) -> int:
    if count <= 0 or max_count <= 0:
        return 0
    ratio = count / max_count
    if ratio <= 0.25:
        return 1
    if ratio <= 0.50:
        return 2
    if ratio <= 0.75:
        return 3
    return 4


def _weekday_name(day_index: int) -> str:
    return ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"][day_index]


def _hour_bucket(hour: int) -> str:
    end = (hour + 1) % 24
    return f"{hour:02d}:00-{end:02d}:00"


def _date_streaks(active_days: list[date], today: date) -> tuple[int, int]:
    if not active_days:
        return 0, 0
    active = set(active_days)
    cursor = today if today in active else today - timedelta(days=1)
    current = 0
    while cursor in active:
        current += 1
        cursor -= timedelta(days=1)

    longest = run = 1
    for index in range(1, len(active_days)):
        if (active_days[index] - active_days[index - 1]).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    return current, longest


def _contributor_insights(
    *,
    commits: list[Commit],
    commits_30: int,
    current_streak: int,
    participation: int,
    peak_hour: int | None,
) -> list[dict[str, str]]:
    insights: list[dict[str, str]] = []
    if peak_hour is not None:
        if peak_hour >= 22 or peak_hour < 5:
            insights.append(
                {
                    "title": "Late-night coding pattern",
                    "detail": "Hoạt động mạnh vào khung giờ khuya.",
                    "tone": "info",
                }
            )
        elif 9 <= peak_hour <= 17:
            insights.append(
                {
                    "title": "Business-hour rhythm",
                    "detail": "Nhịp commit tập trung trong giờ làm việc.",
                    "tone": "positive",
                }
            )
    if participation >= 3:
        insights.append(
            {
                "title": "High repository participation",
                "detail": f"Đóng góp trên {participation} repository.",
                "tone": "positive",
            }
        )
    if current_streak >= 3:
        insights.append(
            {
                "title": "Consistent contribution streak",
                "detail": f"Duy trì chuỗi {current_streak} ngày hoạt động.",
                "tone": "positive",
            }
        )
    if commits_30 == 0 and commits:
        insights.append(
            {
                "title": "Activity cooled down",
                "detail": "Chưa phát hiện commit mới trong 30 ngày qua.",
                "tone": "warning",
            }
        )
    if not insights:
        insights.append(
            {
                "title": "Baseline profile ready",
                "detail": "Cần thêm hoạt động để phát hiện xu hướng rõ hơn.",
                "tone": "info",
            }
        )
    return insights[:4]


def _empty_health_score() -> dict[str, Any]:
    return {
        "score": 0,
        "status": {"label": "Critical", "tone": "critical"},
        "recommendation": "Import and sync a repository to calculate health signals.",
        "primary_insight": "No repository activity has been synced yet.",
        "metrics": {
            "commit_frequency": 0,
            "issue_resolution": 0,
            "pr_merge_speed": 0,
            "contributor_activity": 0,
            "stale_issue_ratio": 0,
            "inactive_days": 0,
        },
        "raw": {
            "commits_last_7_days": 0,
            "previous_7_day_commits": 0,
            "activity_delta_percent": 0,
            "closed_issues": 0,
            "open_issues": 0,
            "stale_issues": 0,
            "stale_issue_ratio": 0,
            "avg_pr_merge_hours": None,
            "active_contributors": 0,
            "inactive_days": None,
        },
        "breakdown": [
            {"label": "Nhịp commit", "value": 0},
            {"label": "Xử lý issue", "value": 0},
            {"label": "Tốc độ merge PR", "value": 0},
            {"label": "Hoạt động contributor", "value": 0},
            {"label": "Issue tồn đọng", "value": 0},
            {"label": "Hoạt động gần đây", "value": 0},
        ],
    }


def _empty_heatmap(today: date) -> dict[str, Any]:
    start = today - timedelta(days=364)
    return {
        "days": [
            {
                "date": (start + timedelta(days=offset)).isoformat(),
                "count": 0,
                "level": 0,
                "label": f"0 commit vào {(start + timedelta(days=offset)).strftime('%d/%m')}",
            }
            for offset in range(365)
        ],
        "max_count": 0,
        "total_commits": 0,
    }


def _empty_team_dashboard() -> dict[str, Any]:
    return {
        "leaderboard": [],
        "members": [],
        "top_contributors": [],
        "issue_resolvers": [],
        "pr_activity": [],
        "summary": {
            "contributors": 0,
            "active_days": 0,
            "commits": 0,
            "issues_closed": 0,
            "prs_merged": 0,
        },
    }


def _empty_kpi_rankings() -> dict[str, Any]:
    empty_person = {"name": "N/A", "login": None, "value": 0, "detail": "Chưa ghi nhận hoạt động"}
    return {
        "top_contributor": empty_person,
        "top_issue_resolver": empty_person,
        "fastest_reviewer": {"name": "N/A", "login": None, "value": "N/A", "detail": "Chưa có pull request được merge"},
        "most_active_repo": {"full_name": "N/A", "score": 0, "commits": 0, "issues_closed": 0, "prs_merged": 0},
    }


def _empty_kpi_charts() -> dict[str, Any]:
    return {
        "commits_by_contributor": [],
        "commits_per_repo": [],
        "issues_resolved_by_user": [],
    }


def _kpi_person(row: dict[str, Any] | None, metric: str) -> dict[str, Any]:
    if not row:
        return {"name": "N/A", "login": None, "value": 0, "detail": "Chưa ghi nhận hoạt động"}
    labels = {
        "commits": "commit",
        "issues_closed": "issue đã xử lý",
        "prs_merged": "PR đã merge",
    }
    return {
        "name": row.get("login") or row.get("name") or "Unknown",
        "login": row.get("login"),
        "avatar_url": row.get("avatar_url"),
        "value": row.get(metric, 0),
        "detail": f"{row.get(metric, 0)} {labels.get(metric, metric)}",
    }


def _fmt_commit(c) -> dict[str, Any]:
    return {
        "sha": c.sha[:7],
        "sha_full": c.sha,
        "message": (c.message or "")[:120],
        "author_name": c.author_name,
        "author_login": c.author_login,
        "author_avatar_url": c.author_avatar_url,
        "committed_at": _vn_iso(c.committed_at),
        "html_url": c.html_url,
        "branch_name": c.branch_name,
    }


def _fmt_pr(p) -> dict[str, Any]:
    return {
        "number": p.number,
        "title": p.title[:120],
        "state": p.state,
        "is_merged": p.is_merged,
        "author_login": p.author_login,
        "author_avatar_url": p.author_avatar_url,
        "created_at": _vn_iso(p.created_at),
        "merged_at": _vn_iso(p.merged_at),
        "closed_at": _vn_iso(p.closed_at),
        "html_url": p.html_url,
        "base_branch": p.base_branch,
        "head_branch": p.head_branch,
    }


def _fmt_issue(i) -> dict[str, Any]:
    return {
        "number": i.number,
        "title": i.title[:120],
        "state": i.state,
        "author_login": i.author_login,
        "labels": i.labels or [],
        "created_at": _vn_iso(i.created_at),
        "closed_at": _vn_iso(i.closed_at),
        "html_url": i.html_url,
    }
