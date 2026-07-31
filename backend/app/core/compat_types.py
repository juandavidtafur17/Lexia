from sqlalchemy import JSON, String
from sqlalchemy.types import TypeDecorator
import uuid

from app.core.config import settings


class GUID(TypeDecorator):
    impl = String(36)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return uuid.UUID(value)
        except Exception:
            return value


def _uuid_fallback(*_args, **_kwargs):
    return GUID()


def _array_fallback(_item_type=None):
    return JSON


# Use Postgres-specific types only when the configured DB is Postgres.
# For sqlite (local dev) provide JSON/String fallbacks to keep models portable.
if settings.DATABASE_URL.startswith("sqlite"):
    ARRAY = _array_fallback
    JSONB = JSON
    UUID = _uuid_fallback
else:
    from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID  # type: ignore
