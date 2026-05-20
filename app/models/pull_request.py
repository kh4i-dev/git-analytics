from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.contributor import Contributor
    from app.models.repository import Repository


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("repo_id", "number", name="uq_pull_requests_repo_number"),
        Index("ix_prs_repo_state", "repo_id", "state"),
        Index("ix_prs_repo_created", "repo_id", "created_at"),
        Index("ix_prs_repo_merged", "repo_id", "merged_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repo_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    contributor_id: Mapped[int | None] = mapped_column(
        ForeignKey("contributors.id", ondelete="SET NULL"),
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    is_merged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    author_login: Mapped[str] = mapped_column(String(255), nullable=False)
    author_avatar_url: Mapped[str | None] = mapped_column(String(500))
    draft: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    html_url: Mapped[str] = mapped_column(String(500), nullable=False)

    repository: Mapped["Repository"] = relationship(back_populates="pull_requests")
    contributor: Mapped["Contributor | None"] = relationship(back_populates="pull_requests")
