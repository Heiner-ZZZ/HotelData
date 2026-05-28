from __future__ import annotations

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


def security_overview(limit: int = 20) -> dict[str, Any]:
    db = get_database()
    return {
        "users": [_clean(item) for item in db.users.find({}, {"password_hash": 0}).sort("created_at", -1).limit(limit)],
        "roles": [_clean(item) for item in db.roles.find({}).sort("role_name", 1)],
        "permissions": [_clean(item) for item in db.permissions.find({}).sort("permission_code", 1)],
        "sessions": [_clean(item) for item in db.user_sessions.find({}).sort("created_at", -1).limit(limit)],
        "activity": [_clean(item) for item in db.user_activity_logs.find({}).sort("created_at", -1).limit(limit)],
        "counts": {
            "users": db.users.count_documents({}),
            "roles": db.roles.count_documents({}),
            "permissions": db.permissions.count_documents({}),
            "sessions": db.user_sessions.count_documents({}),
            "activity": db.user_activity_logs.count_documents({}),
        },
    }


def users_overview(limit: int = 50) -> dict[str, Any]:
    db = get_database()
    users = [_clean(item) for item in db.users.find({}, {"password_hash": 0}).sort("created_at", -1).limit(limit)]
    roles = {str(item["_id"]): item.get("role_name") for item in db.roles.find({})}
    for user in users:
        user["role_names"] = [roles.get(str(role_id), str(role_id)) for role_id in user.get("role_ids", [])]
    return {
        "users": users,
        "roles": [_clean(item) for item in db.roles.find({}).sort("role_name", 1)],
        "counts": {
            "users": db.users.count_documents({}),
            "roles": db.roles.count_documents({}),
        },
    }
