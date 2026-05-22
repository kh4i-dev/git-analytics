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
    from app.models.user import User


class AiProviderSetting(Base):
    __tablename__ = "ai_provider_settings"
    __table_args__ = (
        CheckConstraint("mode IN ('byok', 'cloud')", name="ck_ai_provider_settings_mode"),
        CheckConstraint(
            "provider IN ('openai', 'gemini', 'claude', 'nvidia')",
            name="ck_ai_provider_settings_provider",
        ),
        CheckConstraint(
            "((mode = 'byok' AND encrypted_api_key IS NOT NULL) OR "
            "(mode = 'cloud' AND encrypted_api_key IS NULL))",
            name="ck_ai_provider_settings_key_by_mode",
        ),
        UniqueConstraint(
            "user_id",
            "mode",
            "provider",
            name="uq_ai_provider_settings_user_mode_provider",
        ),
        Index("ix_ai_provider_settings_user_id", "user_id"),
        Index("ix_ai_provider_settings_user_default", "user_id", "is_default"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    encrypted_api_key: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
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

    user: Mapped["User"] = relationship(back_populates="ai_provider_settings")
