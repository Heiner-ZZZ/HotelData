"""User search — find registered users for fast guest data prefill."""

from __future__ import annotations

import re
from typing import Any

from pymongo import ASCENDING


def search_users(
    q: str,
    limit: int = 10,
    db=None,
) -> list[dict[str, Any]]:
    """Search registered users by name or email for quick guest data prefill."""
    regex = {"$regex": re.escape(q), "$options": "i"}
    users = list(
        db.users.find(
            {"$or": [{"display_name": regex}, {"email": regex}]},
            {"_id": 0, "display_name": 1, "email": 1, "phone": 1, "cedula": 1},
        )
        .sort([("display_name", ASCENDING)])
        .limit(limit)
    )
    return [
        {
            "name": u.get("display_name", ""),
            "email": u.get("email", ""),
            "phone": u.get("phone", ""),
            "cedula": u.get("cedula", ""),
        }
        for u in users
    ]
