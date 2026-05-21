from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.contributor import Contributor
    from app.models.repository import Repository


class Commit(Base):
    __tablename__ = "commits"
    __table_args__ = (
        UniqueConstraint("repo_id", "sha", name="uq_commits_repo_sha"),
        Index("ix_commits_repo_date", "repo_id", "committed_at"),
        Index("ix_commits_repo_author", "repo_id", "author_login"),
        Index("ix_commits_repo_branch", "repo_id", "branch_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repo_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    contributor_id: Mapped[int | None] = mapped_column(
        ForeignKey("contributors.id", ondelete="SET NULL"),
    )
    sha: Mapped[str] = mapped_column(String(40), nullable=False)
    branch_name: Mapped[str | None] = mapped_column(String(255))
    message: Mapped[str | None] = mapped_column(Text)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    author_email: Mapped[str] = mapped_column(String(255), nullable=False)
    author_login: Mapped[str | None] = mapped_column(String(255))
    author_avatar_url: Mapped[str | None] = mapped_column(String(500))
    committer_name: Mapped[str | None] = mapped_column(String(255))
    committer_email: Mapped[str | None] = mapped_column(String(255))
    committer_login: Mapped[str | None] = mapped_column(String(255))
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    html_url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    repository: Mapped["Repository"] = relationship(back_populates="commits")
    contributor: Mapped["Contributor | None"] = relationship(back_populates="commits")

    @property
    def repository_id(self) -> int:
        return self.repo_id

    @repository_id.setter
    def repository_id(self, value: int) -> None:
        self.repo_id = value
