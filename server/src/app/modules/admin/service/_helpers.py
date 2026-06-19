from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from src.database.connection import get_database


def _clean(document: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(document)
    for key, value in list(cleaned.items()):
        if isinstance(value, ObjectId):
            cleaned[key] = str(value)
        elif isinstance(value, list):
            cleaned[key] = [str(item) if isinstance(item, ObjectId) else item for item in value]
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
