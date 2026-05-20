from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.branch import Branch
    from app.models.commit import Commit
    from app.models.contributor import Contributor
    from app.models.issue import Issue
    from app.models.pull_request import PullRequest
    from app.models.user import User


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("user_id", "github_repo_id", name="uq_repositories_user_repo"),
        CheckConstraint(
            "last_sync_status IN ('pending', 'syncing', 'success', 'failed')",
            name="ck_repositories_last_sync_status",
        ),
        Index("ix_repositories_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    github_repo_id: Mapped[int] = mapped_column(Integer, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(100))
    is_private: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    default_branch: Mapped[str | None] = mapped_column(String(255))
    branch_sync_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="default_only",
        server_default="default_only",
    )
    selected_branches: Mapped[str | None] = mapped_column(Text)
    html_url: Mapped[str] = mapped_column(String(500), nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    last_sync_error: Mapped[str | None] = mapped_column(Text)
    sync_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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

    user: Mapped["User"] = relationship(back_populates="repositories")
    contributors: Mapped[list["Contributor"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    commits: Mapped[list["Commit"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    branches: Mapped[list["Branch"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    pull_requests: Mapped[list["PullRequest"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    issues: Mapped[list["Issue"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )
