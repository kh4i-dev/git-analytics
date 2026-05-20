from collections.abc import Mapping
from typing import Any, Generic, NoReturn, TypeVar

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DatabaseException,
    DatabaseIntegrityException,
    ValidationException,
)

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    def __init__(self, db: Session) -> None:
        self.db = db

    def _flush(self) -> None:
        try:
            self.db.flush()
        except IntegrityError as exc:
            raise DatabaseIntegrityException(
                "Database constraint violation.",
                details={"error": str(exc.orig)},
            ) from exc
        except SQLAlchemyError as exc:
            raise DatabaseException(details={"error": str(exc)}) from exc

    def _apply_updates(self, instance: ModelT, data: Mapping[str, Any]) -> ModelT:
        for field, value in data.items():
            setattr(instance, field, value)
        self._flush()
        return instance

    def _pagination(self, page: int, per_page: int) -> tuple[int, int]:
        if page < 1:
            raise ValidationException("page must be greater than or equal to 1.")
        if per_page < 1 or per_page > 100:
            raise ValidationException("per_page must be between 1 and 100.")
        return (page - 1) * per_page, per_page

    def _raise_database_error(self, exc: SQLAlchemyError) -> NoReturn:
        raise DatabaseException(details={"error": str(exc)}) from exc
