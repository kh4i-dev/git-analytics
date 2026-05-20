from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.commit import Commit
    from app.models.issue import Issue
    from app.models.pull_request import PullRequest
    from app.models.repository import Repository


class Contributor(Base):
    __tablename__ = "contributors"
    __table_args__ = (
        UniqueConstraint(
            "repo_id",
            "github_login",
            "email",
            name="uq_contributors_repo_identity",
        ),
        CheckConstraint(
            "source_type IN ('github_user', 'git_email')",
            name="ck_contributors_source_type",
        ),
        Index("ix_contributors_repo_id", "repo_id"),
        Index("ix_contributors_repo_login", "repo_id", "github_login"),
        Index("ix_contributors_repo_email", "repo_id", "email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repo_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    github_login: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
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

    repository: Mapped["Repository"] = relationship(back_populates="contributors")
    commits: Mapped[list["Commit"]] = relationship(back_populates="contributor")
    pull_requests: Mapped[list["PullRequest"]] = relationship(back_populates="contributor")
    issues: Mapped[list["Issue"]] = relationship(back_populates="contributor")
