from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.models.ai_usage_event import AiUsageEvent
from app.repositories.base import BaseRepository


class AiUsageRepository(BaseRepository[AiUsageEvent]):
    def count_cloud_requests_since(self, user_id: int, since: datetime) -> int:
        try:
            return int(
                self.db.scalar(
                    select(func.count(AiUsageEvent.id)).where(
                        AiUsageEvent.user_id == user_id,
                        AiUsageEvent.mode == "cloud",
                        AiUsageEvent.created_at >= since,
                    )
                )
                or 0
            )
        except SQLAlchemyError as exc:
            self._raise_database_error(exc)

    def create_event(
        self,
        *,
        user_id: int,
        mode: str,
        provider: str,
        operation: str,
        status: str,
        usage_units: int | None = None,
    ) -> AiUsageEvent:
        event = AiUsageEvent(
            user_id=user_id,
            mode=mode,
            provider=provider,
            operation=operation,
            status=status,
            usage_units=usage_units,
        )
        self.db.add(event)
        self._flush()
        return event
