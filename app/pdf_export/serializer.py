from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReportSummary:
    total_repositories: int = 0
    synced_repositories: int = 0
    total_commits: int = 0
    total_prs: int = 0
    total_issues: int = 0
    total_contributors: int = 0
    active_repositories: int = 0
    commits_last_7: int = 0
    most_active_repo: str = "N/A"
    top_contributor: str = "N/A"


@dataclass
class KPIItem:
    label: str
    value: str
    detail: str = ""


@dataclass
class ReportHealth:
    score: int = 0
    status: str = "Unknown"
    recommendation: str = ""
    breakdown: list[dict] = field(default_factory=list)


@dataclass
class ReportTeam:
    columns: list[str] = field(default_factory=list)
    col_widths: list[float] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class ReportData:
    title: str = "Git Analytics Engineering Report"
    generated_at: str = ""
    username: str = ""
    repository_scope: str = "All Repositories"
    export_type: str = "PDF Export"

    summary: ReportSummary = field(default_factory=ReportSummary)
    health: ReportHealth = field(default_factory=ReportHealth)
    kpi_rankings: list[KPIItem] = field(default_factory=list)
    team: ReportTeam = field(default_factory=ReportTeam)
    insights: list[str] = field(default_factory=list)


class ReportSerializer:
    def serialize(self, stats: dict[str, Any], username: str | None = None) -> ReportData:
        summary_data = stats.get("summary", {})
        health_data = stats.get("health", {})
        kpi_data = stats.get("kpi", {})
        team_data = stats.get("team", {})
        insights_data = stats.get("insights", [])

        summary = ReportSummary(
            total_repositories=summary_data.get("total_repositories", 0),
            synced_repositories=summary_data.get("synced_repositories", 0),
            total_commits=summary_data.get("total_commits", 0),
            total_prs=summary_data.get("total_prs", 0),
            total_issues=summary_data.get("total_issues", 0),
            total_contributors=summary_data.get("total_contributors", 0),
            active_repositories=summary_data.get("active_repositories", 0),
            commits_last_7=summary_data.get("commits_last_7_days", 0),
            most_active_repo=summary_data.get("most_active_repository", {}).get("full_name", "N/A"),
            top_contributor=summary_data.get("top_contributor", {}).get("name", "N/A"),
        )

        health = ReportHealth(
            score=health_data.get("score", 0),
            status=health_data.get("status", {}).get("label", "Unknown"),
            recommendation=health_data.get("recommendation", ""),
            breakdown=health_data.get("breakdown", []),
        )

        kpi_rankings = [
            KPIItem(
                label="Top Contributor",
                value=str(kpi_data.get("top_contributor", {}).get("name", "N/A")),
                detail=f"{kpi_data.get('top_contributor', {}).get('value', 0)} commits",
            ),
            KPIItem(
                label="Top Issue Resolver",
                value=str(kpi_data.get("top_issue_resolver", {}).get("name", "N/A")),
                detail=f"{kpi_data.get('top_issue_resolver', {}).get('value', 0)} resolved",
            ),
            KPIItem(
                label="Fastest Reviewer",
                value=str(kpi_data.get("fastest_reviewer", {}).get("name", "N/A")),
                detail=kpi_data.get("fastest_reviewer", {}).get("detail", ""),
            ),
            KPIItem(
                label="Most Active Repo",
                value=str(kpi_data.get("most_active_repo", {}).get("full_name", "N/A")),
                detail=f"Score: {kpi_data.get('most_active_repo', {}).get('score', 0)}",
            ),
        ]

        members = team_data.get("members", [])
        team = ReportTeam(
            columns=["Contributor", "Commits", "PR Merged", "Issues", "Active Days", "Score"],
            col_widths=[48, 24, 24, 24, 24, 26],
            rows=[
                [
                    str(m.get("login") or m.get("name") or "Unknown")[:20],
                    str(m.get("commits", 0)),
                    str(m.get("prs_merged", 0)),
                    str(m.get("issues_closed", 0)),
                    str(m.get("active_days", 0)),
                    str(m.get("score", 0)),
                ]
                for m in members
            ],
        )

        insight_labels = [i.get("title", "") for i in insights_data[:4]]

        return ReportData(
            generated_at=self._now_string(),
            username=username or "User",
            repository_scope=summary_data.get("most_active_repository", {}).get("full_name", "All Repositories"),
            export_type="PDF Export",
            summary=summary,
            health=health,
            kpi_rankings=kpi_rankings,
            team=team,
            insights=insight_labels,
        )

    def _now_string(self) -> str:
        from datetime import UTC, datetime
        return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
