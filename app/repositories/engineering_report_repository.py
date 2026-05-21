from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.engineering_report import RepositoryEngineeringReport
from app.repositories.base import BaseRepository


class EngineeringReportRepository(BaseRepository[RepositoryEngineeringReport]):
    def get_by_id(self, report_id: int) -> RepositoryEngineeringReport | None:
        try:
            return self.db.get(RepositoryEngineeringReport, report_id)
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_by_user_and_id(
        self,
        user_id: int,
        report_id: int,
    ) -> RepositoryEngineeringReport | None:
        try:
            return self.db.scalar(
                select(RepositoryEngineeringReport).where(
                    RepositoryEngineeringReport.user_id == user_id,
                    RepositoryEngineeringReport.id == report_id,
                    RepositoryEngineeringReport.deleted_at.is_(None),
                )
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_by_public_token(self, public_token: str) -> RepositoryEngineeringReport | None:
        try:
            return self.db.scalar(
                select(RepositoryEngineeringReport).where(
                    RepositoryEngineeringReport.public_token == public_token,
                    RepositoryEngineeringReport.revoked_at.is_(None),
                    RepositoryEngineeringReport.deleted_at.is_(None),
                )
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def list_by_user(
        self,
        user_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> Sequence[RepositoryEngineeringReport]:
        offset, limit = self._pagination(page, per_page)
        try:
            return self.db.scalars(
                select(RepositoryEngineeringReport)
                .where(
                    RepositoryEngineeringReport.user_id == user_id,
                    RepositoryEngineeringReport.deleted_at.is_(None),
                )
                .order_by(
                    RepositoryEngineeringReport.generated_at.desc(),
                    RepositoryEngineeringReport.id.desc(),
                )
                .offset(offset)
                .limit(limit)
            ).all()
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def get_latest_for_repository(
        self,
        repository_id: int,
    ) -> RepositoryEngineeringReport | None:
        try:
            return self.db.scalar(
                select(RepositoryEngineeringReport)
                .where(
                    RepositoryEngineeringReport.repository_id == repository_id,
                    RepositoryEngineeringReport.deleted_at.is_(None),
                )
                .order_by(
                    RepositoryEngineeringReport.to_date.desc(),
                    RepositoryEngineeringReport.id.desc(),
                )
                .limit(1)
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def create(self, data: Mapping[str, Any]) -> RepositoryEngineeringReport:
        report = RepositoryEngineeringReport(**data)
        self.db.add(report)
        self._flush()
        return report

    def update(
        self,
        report: RepositoryEngineeringReport,
        data: Mapping[str, Any],
    ) -> RepositoryEngineeringReport:
        return self._apply_updates(report, data)
