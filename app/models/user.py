from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ai_provider_setting import AiProviderSetting
    from app.models.ai_usage_event import AiUsageEvent
    from app.models.engineering_report import RepositoryEngineeringReport
    from app.models.repository import Repository


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    github_login: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    encrypted_github_token: Mapped[str] = mapped_column(Text, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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

    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    engineering_reports: Mapped[list["RepositoryEngineeringReport"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    ai_provider_settings: Mapped[list["AiProviderSetting"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    ai_usage_events: Mapped[list["AiUsageEvent"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
