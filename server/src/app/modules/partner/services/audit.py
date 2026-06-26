"""Universal audit service for the partner module.

Logs all CRUD operations (room types, inventory, rates, policies, amenities, content)
to a single `audit_log` collection for centralized viewing and filtering.

Every entry includes:
- timestamp, actor (changed_by), action (create/update/delete)
- entity_type (room_type, inventory_entry, rate_plan, policy, amenity, content)
- entity_id (the primary identifier of the affected record)
- prop_id (property context)
- summary (human-readable one-liner)
- diff (optional structured dict of changed fields)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.database.connection import get_database


def ensure_audit_indexes():
    """Ensure indexes for audit_log collection for query performance."""
    db = get_database()
    db.audit_log.create_index([("timestamp", -1)])
    db.audit_log.create_index([("prop_id", 1), ("timestamp", -1)])
    db.audit_log.create_index([("entity_type", 1), ("timestamp", -1)])


def now_utc() -> datetime:
    return datetime.now(UTC)


def register_action(
    *,
    prop_id: int,
    entity_type: str,
    entity_id: str,
    action: str,
    summary: str,
    changed_by: str = "system",
    diff: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Register a single auditable action.

    Parameters
    ----------
    prop_id : int
        Property (hotel) identifier.
    entity_type : str
        Logical type of the affected entity, e.g. ``"room_type"``,
        ``"inventory_entry"``, ``"rate_plan"``, ``"policy"``, ``"amenity"``.
    entity_id : str
        Primary identifier of the affected record within its collection.
    action : str
        One of ``"create"``, ``"update"``, ``"delete"``, ``"soft_delete"``,
        ``"restore"``, ``"batch_update"``.
    summary : str
        Short human-readable description in Spanish.
    changed_by : str
        Who performed the action (default ``"system"``).
    diff : dict or None
        Dict of ``{field_name: {"old": old_value, "new": new_value}}``
        representing what actually changed.
    metadata : dict or None
        Any additional free-form context (e.g. ``{"room_type_name": "Suite"}``).
    """
    db = get_database()
    entry: dict[str, Any] = {
        "timestamp": now_utc(),
        "prop_id": prop_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "summary": summary,
        "changed_by": changed_by,
    }
    if diff:
        entry["diff"] = diff
    if metadata:
        entry["metadata"] = metadata
    db.audit_log.insert_one(entry)


def list_audit_entries(
    *,
    prop_id: int | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    changed_by: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = 1,
    per_page: int = 30,
) -> dict[str, Any]:
    """Return paginated, filtered audit log entries, newest first."""
    db = get_database()
    page = max(page, 1)
    per_page = min(max(per_page, 1), 200)

    query: dict[str, Any] = {}
    if prop_id is not None and prop_id > 0:
        query["prop_id"] = prop_id
    if entity_type:
        query["entity_type"] = entity_type
    if action:
        query["action"] = action
    if changed_by:
        query["changed_by"] = changed_by
    if from_date or to_date:
        date_filter: dict[str, str] = {}
        if from_date:
            date_filter["$gte"] = from_date
        if to_date:
            date_filter["$lte"] = to_date
        if date_filter:
            query["timestamp"] = date_filter

    total = db.audit_log.count_documents(query)
    items = list(
        db.audit_log.find(query, {"_id": 0})
        .sort([("timestamp", -1)])
        .skip((page - 1) * per_page)
        .limit(per_page)
    )

    # Serialize datetimes
    for item in items:
        ts = item.get("timestamp")
        if hasattr(ts, "isoformat"):
            item["timestamp"] = ts.isoformat()

    pages = (total + per_page - 1) // per_page if total else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1 and pages > 0,
    }


def get_audit_stats(
    prop_id: int | None = None,
) -> dict[str, Any]:
    """Return aggregate statistics for the audit log."""
    db = get_database()
    query: dict[str, Any] = {}
    if prop_id is not None and prop_id > 0:
        query["prop_id"] = prop_id

    pipeline: list[dict[str, Any]] = [
        {"$match": query},
        {
            "$group": {
                "_id": "$entity_type",
                "count": {"$sum": 1},
                "last_action": {"$max": "$timestamp"},
            },
        },
        {"$sort": {"count": -1}},
    ]
    by_entity = list(db.audit_log.aggregate(pipeline))
    for entry in by_entity:
        ts = entry.get("last_action")
        if hasattr(ts, "isoformat"):
            entry["last_action"] = ts.isoformat()
        entry["entity_type"] = entry.pop("_id")

    today_pipeline: list[dict[str, Any]] = [
        {"$match": {**query, "timestamp": {"$gte": now_utc().replace(hour=0, minute=0, second=0, microsecond=0)}}},
        {"$count": "today"},
    ]
    today_result = list(db.audit_log.aggregate(today_pipeline))
    today_count = today_result[0]["today"] if today_result else 0

    return {
        "total_entries": db.audit_log.count_documents(query),
        "today_entries": today_count,
        "by_entity": by_entity,
    }
