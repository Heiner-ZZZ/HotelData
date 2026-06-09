from __future__ import annotations

from src.database.connection import get_database


def recent_activity(limit: int = 20) -> dict[str, list[dict]]:
    db = get_database()
    return {
        "etl_executions": list(
            db.etl_executions.find({}, {"_id": 0}).sort("executed_at", -1).limit(limit)
        ),
        "search_logs": list(
            db.search_logs.find({}, {"_id": 0}).sort("searched_at", -1).limit(limit)
        ),
    }
