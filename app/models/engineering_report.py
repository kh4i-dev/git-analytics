from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.user import User


class RepositoryEngineeringReport(Base):
    __tablename__ = "repository_engineering_reports"
    __table_args__ = (
        Index("ix_reports_user_generated", "user_id", "generated_at"),
        Index("ix_reports_repo_range", "repository_id", "from_date", "to_date"),
        Index("ix_reports_public_token", "public_token", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    to_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    staleness_threshold_hours_used: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_title: Mapped[str] = mapped_column(String(500), nullable=False)
    custom_title: Mapped[str | None] = mapped_column(String(500))
    display_repository_name: Mapped[str | None] = mapped_column(String(500))
    is_repository_anonymized: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    summary_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    release_notes_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    changelog_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    risk_insights: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    public_token: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="engineering_reports")
    repository: Mapped["Repository"] = relationship(back_populates="engineering_reports")
