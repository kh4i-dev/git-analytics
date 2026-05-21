from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import RepositoryNotFoundException, ValidationException
from app.models.commit import Commit
from app.models.engineering_report import RepositoryEngineeringReport
from app.models.issue import Issue
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.repositories.engineering_report_repository import EngineeringReportRepository
from app.repositories.repository_repo import RepositoryRepository
from app.services.changelog_service import ChangelogService
from app.services.release_notes_service import ReleaseNotesService
from app.services.risk_insight_service import RiskInsightService


class EngineeringReportService:
    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _ensure_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationException("Report date must be ISO 8601.") from exc
        return EngineeringReportService._ensure_aware(parsed)

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        if value is None:
            return None
        return EngineeringReportService._ensure_aware(value).isoformat()

    @staticmethod
    def _resolve_date_range(
        db: Session,
        repo: Repository,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> tuple[datetime, datetime, str]:
        explicit_from = EngineeringReportService._parse_date(from_date)
        explicit_to = EngineeringReportService._parse_date(to_date)
        resolved_to = explicit_to or EngineeringReportService._now()

        if explicit_from is not None:
            resolved_from = explicit_from
            source = "explicit"
        else:
            latest = EngineeringReportRepository(db).get_latest_for_repository(repo.id)
            if latest is not None:
                resolved_from = EngineeringReportService._ensure_aware(latest.to_date)
                source = "continuity"
            else:
                lookback_start = resolved_to - timedelta(days=settings.report_default_lookback_days)
                repo_created_at = EngineeringReportService._ensure_aware(repo.created_at)
                resolved_from = max(repo_created_at, lookback_start)
                source = "first_report_fallback"

        if resolved_from >= resolved_to:
            raise ValidationException("Report from_date must be before to_date.")
        return resolved_from, resolved_to, source

    @staticmethod
    def _count_between(db: Session, model: type[Any], date_field: Any, repo_id: int, start: datetime, end: datetime) -> int:
        return int(
            db.scalar(
                select(func.count())
                .select_from(model)
                .where(
                    model.repo_id == repo_id,
                    date_field >= start,
                    date_field <= end,
                )
            )
            or 0
        )

    @staticmethod
    def _build_summary(
        db: Session,
        repo: Repository,
        *,
        from_date: datetime,
        to_date: datetime,
        range_source: str,
        risks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        commit_count = EngineeringReportService._count_between(
            db,
            Commit,
            Commit.committed_at,
            repo.id,
            from_date,
            to_date,
        )
        pr_count = EngineeringReportService._count_between(
            db,
            PullRequest,
            PullRequest.created_at,
            repo.id,
            from_date,
            to_date,
        )
        issue_count = EngineeringReportService._count_between(
            db,
            Issue,
            Issue.created_at,
            repo.id,
            from_date,
            to_date,
        )
        high_risks = sum(1 for risk in risks if risk.get("severity") == "high")
        medium_risks = sum(1 for risk in risks if risk.get("severity") == "medium")
        low_risks = sum(1 for risk in risks if risk.get("severity") == "low")
        data_synced_at = EngineeringReportService._ensure_aware(repo.last_synced_at) if repo.last_synced_at else None
        stale_after = timedelta(hours=settings.report_staleness_threshold_hours)
        is_stale = data_synced_at is None or EngineeringReportService._now() - data_synced_at > stale_after

        return {
            "repository_full_name": repo.full_name,
            "report_access_model": "capability_url",
            "report_indexing": "noindex_nofollow",
            "report_lifecycle": {
                "password_required": False,
                "expires_at": None,
                "billing_tier": "free",
            },
            "from_date": EngineeringReportService._iso(from_date),
            "to_date": EngineeringReportService._iso(to_date),
            "range_source": range_source,
            "data_synced_at": EngineeringReportService._iso(data_synced_at),
            "is_data_stale": is_stale,
            "counts": {
                "commits": commit_count,
                "pull_requests": pr_count,
                "issues": issue_count,
                "risks": len(risks),
            },
            "risk_summary": {
                "high": high_risks,
                "medium": medium_risks,
                "low": low_risks,
            },
        }

    @staticmethod
    def _build_ai_summary(
        *,
        repo: Repository,
        release_notes: dict[str, Any],
        changelog: dict[str, Any],
        risks: list[dict[str, Any]],
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        counts = summary["counts"]
        risk_summary = summary["risk_summary"]
        total_changes = counts["commits"] + counts["pull_requests"] + counts["issues"]
        if total_changes == 0:
            headline = "No notable engineering activity was captured for this period."
        elif risk_summary["high"] > 0:
            headline = f"{repo.name} shipped activity with {risk_summary['high']} high-priority risk signal(s) to review."
        elif counts["commits"] > 0:
            headline = f"{repo.name} recorded {counts['commits']} commit(s) with no high-priority risk signal."
        else:
            headline = f"{repo.name} had light activity across PRs and issues in this report window."

        release_breakdown = release_notes.get("stats", {}).get("breakdown", {})
        top_change_type = None
        if release_breakdown:
            top_change_type = max(release_breakdown.items(), key=lambda item: item[1])[0]

        bullets = [
            f"Activity window covers {summary['from_date']} to {summary['to_date']}.",
            f"Snapshot includes {counts['commits']} commits, {counts['pull_requests']} pull requests, and {counts['issues']} issues.",
        ]
        if top_change_type:
            bullets.append(f"Most common change group: {top_change_type}.")
        if counts["risks"]:
            bullets.append(
                f"Risk scan found {counts['risks']} signal(s): {risk_summary['high']} high, {risk_summary['medium']} medium, {risk_summary['low']} low."
            )
        else:
            bullets.append("Risk scan did not find any signals for this repository snapshot.")

        return {
            "mode": "rule_based",
            "headline": headline,
            "bullets": bullets,
            "changelog_groups": len(changelog.get("sections", {})),
        }

    @staticmethod
    def create_report(
        db: Session,
        *,
        user_id: int,
        repository_id: int,
        from_date: str | None = None,
        to_date: str | None = None,
        custom_title: str | None = None,
    ) -> RepositoryEngineeringReport:
        repo = RepositoryRepository(db).get_by_user_and_id(user_id, repository_id)
        if repo is None:
            raise RepositoryNotFoundException("Repository not found.")

        resolved_from, resolved_to, range_source = EngineeringReportService._resolve_date_range(
            db,
            repo,
            from_date=from_date,
            to_date=to_date,
        )
        from_iso = resolved_from.isoformat()
        to_iso = resolved_to.isoformat()

        release_notes = ReleaseNotesService.generate_release_notes(
            db=db,
            repo_id=repo.id,
            from_date=from_iso,
            to_date=to_iso,
        )
        changelog = ChangelogService.generate_changelog(
            db=db,
            repo_id=repo.id,
            from_date=from_iso,
            to_date=to_iso,
        )
        risks = RiskInsightService.detect_risks(db=db, user_id=user_id, repo_id=repo.id)
        summary = EngineeringReportService._build_summary(
            db,
            repo,
            from_date=resolved_from,
            to_date=resolved_to,
            range_source=range_source,
            risks=risks,
        )
        ai_summary = EngineeringReportService._build_ai_summary(
            repo=repo,
            release_notes=release_notes,
            changelog=changelog,
            risks=risks,
            summary=summary,
        )
        summary["ai_summary"] = ai_summary
        generated_at = EngineeringReportService._now()
        generated_title = (
            f"{repo.full_name} · {resolved_from.date().isoformat()} to {resolved_to.date().isoformat()}"
        )

        return EngineeringReportRepository(db).create(
            {
                "user_id": user_id,
                "repository_id": repo.id,
                "from_date": resolved_from,
                "to_date": resolved_to,
                "generated_at": generated_at,
                "data_synced_at": repo.last_synced_at,
                "staleness_threshold_hours_used": settings.report_staleness_threshold_hours,
                "generated_title": generated_title,
                "custom_title": custom_title.strip() if custom_title else None,
                "summary_payload": summary,
                "release_notes_markdown": release_notes["markdown_output"],
                "changelog_markdown": changelog["markdown"],
                "risk_insights": risks,
            }
        )

    @staticmethod
    def publish_report(
        db: Session,
        *,
        user_id: int,
        report_id: int,
        is_repository_anonymized: bool = False,
        display_repository_name: str | None = None,
    ) -> RepositoryEngineeringReport:
        report = EngineeringReportRepository(db).get_by_user_and_id(user_id, report_id)
        if report is None:
            raise RepositoryNotFoundException("Report not found.")

        public_name = display_repository_name.strip() if display_repository_name else None
        public_token = report.public_token
        if public_token is None or report.revoked_at is not None:
            public_token = token_urlsafe(32)

        return EngineeringReportRepository(db).update(
            report,
            {
                "public_token": public_token,
                "published_at": EngineeringReportService._now(),
                "revoked_at": None,
                "is_repository_anonymized": is_repository_anonymized,
                "display_repository_name": public_name,
            },
        )

    @staticmethod
    def revoke_report(db: Session, *, user_id: int, report_id: int) -> RepositoryEngineeringReport:
        report = EngineeringReportRepository(db).get_by_user_and_id(user_id, report_id)
        if report is None:
            raise RepositoryNotFoundException("Report not found.")
        return EngineeringReportRepository(db).update(
            report,
            {
                "public_token": None,
                "revoked_at": EngineeringReportService._now(),
            },
        )

    @staticmethod
    def update_metadata(
        db: Session,
        *,
        user_id: int,
        report_id: int,
        custom_title: str | None,
    ) -> RepositoryEngineeringReport:
        report = EngineeringReportRepository(db).get_by_user_and_id(user_id, report_id)
        if report is None:
            raise RepositoryNotFoundException("Report not found.")
        clean_title = custom_title.strip() if custom_title else None
        return EngineeringReportRepository(db).update(report, {"custom_title": clean_title})

    @staticmethod
    def delete_report(db: Session, *, user_id: int, report_id: int) -> RepositoryEngineeringReport:
        report = EngineeringReportRepository(db).get_by_user_and_id(user_id, report_id)
        if report is None:
            raise RepositoryNotFoundException("Report not found.")
        now = EngineeringReportService._now()
        return EngineeringReportRepository(db).update(
            report,
            {
                "deleted_at": now,
                "revoked_at": now,
                "public_token": None,
            },
        )

    @staticmethod
    def serialize(report: RepositoryEngineeringReport, *, include_private: bool = True) -> dict[str, Any]:
        repository_name = report.repository.full_name
        public_repository_name = repository_name
        if report.is_repository_anonymized:
            public_repository_name = report.display_repository_name or "Private Repository"

        data: dict[str, Any] = {
            "id": report.id,
            "repository_id": report.repository_id,
            "repository_full_name": repository_name if include_private else public_repository_name,
            "public_repository_name": public_repository_name,
            "display_title": report.custom_title or report.generated_title,
            "generated_title": report.generated_title,
            "custom_title": report.custom_title,
            "from_date": EngineeringReportService._iso(report.from_date),
            "to_date": EngineeringReportService._iso(report.to_date),
            "generated_at": EngineeringReportService._iso(report.generated_at),
            "data_synced_at": EngineeringReportService._iso(report.data_synced_at),
            "staleness_threshold_hours_used": report.staleness_threshold_hours_used,
            "summary": report.summary_payload,
            "release_notes_markdown": report.release_notes_markdown,
            "changelog_markdown": report.changelog_markdown,
            "risk_insights": report.risk_insights,
            "is_repository_anonymized": report.is_repository_anonymized,
            "published_at": EngineeringReportService._iso(report.published_at),
            "revoked_at": EngineeringReportService._iso(report.revoked_at),
        }
        if include_private:
            data["public_token"] = report.public_token
            data["public_url"] = f"/r/{report.public_token}" if report.public_token else None
            data["deleted_at"] = EngineeringReportService._iso(report.deleted_at)
        return data

    @staticmethod
    def render_markdown(report: RepositoryEngineeringReport) -> str:
        data = EngineeringReportService.serialize(report)
        lines = [
            f"# {data['display_title']}",
            "",
            f"- Repository: {data['repository_full_name']}",
            f"- Covers: {data['from_date']} to {data['to_date']}",
            f"- Generated: {data['generated_at']}",
            f"- Data synced: {data['data_synced_at'] or 'Never'}",
            "",
            "## Summary",
            "",
            f"- Commits: {data['summary']['counts']['commits']}",
            f"- Pull requests: {data['summary']['counts']['pull_requests']}",
            f"- Issues: {data['summary']['counts']['issues']}",
            f"- Risks: {data['summary']['counts']['risks']}",
            "",
            "## Release Notes",
            "",
            report.release_notes_markdown,
            "",
            "## Changelog",
            "",
            report.changelog_markdown,
            "",
            "## Risk Insights",
            "",
        ]
        if report.risk_insights:
            for risk in report.risk_insights:
                lines.append(f"- **{risk.get('name', 'Risk')}** ({risk.get('severity', 'unknown')}): {risk.get('detail', '')}")
        else:
            lines.append("No risks detected in this snapshot.")
        return "\n".join(lines)
