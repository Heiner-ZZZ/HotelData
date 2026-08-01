from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from src.database.connection import get_database


def _clean(document: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe copy of a Mongo document for API responses."""
    def clean_value(value: Any) -> Any:
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, list):
            return [clean_value(item) for item in value]
        if isinstance(value, dict):
            return {key: clean_value(item) for key, item in value.items()}
        return value

    cleaned = {key: clean_value(value) for key, value in document.items()}
    cleaned.pop("password_hash", None)
    return cleaned


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_user_status_field() -> int:
    db = get_database()
    result = db.users.update_many(
        {"is_active": {"$exists": False}},
        {
            "$set": {
                "is_active": True,
                "updated_at": utc_now(),
                "updated_by": "system.ensure_user_status_field",
            }
        },
    )
    return int(result.modified_count)
