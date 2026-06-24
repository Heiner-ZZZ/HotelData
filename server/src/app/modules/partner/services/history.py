"""History / audit-log queries for partner properties.

Provides paginated listing and detail lookup for changes recorded in
`hotel_profile_changes` (profile edits) and `hotel_content_changes`
(content edits). Both collections are written automatically by the
respective save functions — this module only reads them.
"""
from __future__ import annotations

from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database

from src.database.connection import get_database


def _paginate(page: int, per_page: int, total: int) -> dict[str, Any]:
    pages = (total + per_page - 1) // per_page if total else 0
    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "has_prev": page > 1 and pages > 0,
        "has_next": pages > 0 and page < pages,
    }


def _normalize_change(doc: dict[str, Any]) -> dict[str, Any]:
    """Shape a raw MongoDB document into the API response format."""
    changed_at = doc.get("changed_at")
    return {
        "id": str(doc.get("_id", "")),
        "field": doc.get("field", ""),
        "old_value": doc.get("old_value", ""),
        "new_value": doc.get("new_value", ""),
        "changed_by": doc.get("changed_by", ""),
        "changed_at": changed_at.isoformat() if hasattr(changed_at, "isoformat") else str(changed_at or ""),
        "source": doc.get("source", ""),
        "reason": doc.get("reason", ""),
    }


def list_hotel_changes(
    prop_id: int,
    *,
    from_date: str | None = None,
    to_date: str | None = None,
    field: str | None = None,
    user: str | None = None,
    source: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """Return paginated changes for a property, merged from both audit collections.

    Supports filtering by date range, field, user (changed_by), and source.
    Results are sorted by changed_at descending (most recent first).
    """
    db: Database = get_database()
    page = max(page, 1)
    per_page = min(max(per_page, 1), 200)

    # Build base filter
    base_filter: dict[str, Any] = {"prop_id": prop_id}
    if from_date:
        base_filter["changed_at"] = {"$gte": from_date}
    if to_date:
        date_filter = base_filter.get("changed_at", {})
        date_filter["$lte"] = to_date
        base_filter["changed_at"] = date_filter
    if field:
        base_filter["field"] = field
    if user:
        base_filter["changed_by"] = user

    # Query both collections
    profile_coll: Collection = db.hotel_profile_changes
    content_coll: Collection = db.hotel_content_changes

    profile_total = profile_coll.count_documents(base_filter)
    content_total = content_coll.count_documents({**base_filter, "entity_type": {"$exists": True}})

    # Fetch profile changes
    profile_cursor = (
        profile_coll.find(base_filter, {"_id": 1, "field": 1, "old_value": 1, "new_value": 1,
                                        "changed_by": 1, "changed_at": 1, "source": 1, "reason": 1})
        .sort([("changed_at", -1)])
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    profile_items = [_normalize_change(doc) for doc in profile_cursor]

    # Fetch content changes (if they exist for this prop)
    content_cursor = (
        content_coll.find({**base_filter, "entity_type": {"$exists": True}},
                          {"_id": 1, "field": 1, "old_value": 1, "new_value": 1,
                           "changed_by": 1, "changed_at": 1, "source": 1, "reason": 1})
        .sort([("changed_at", -1)])
        .limit(per_page)
    )
    content_items = [_normalize_change(doc) for doc in content_cursor]

    # Merge & sort
    merged = sorted(profile_items + content_items, key=lambda x: x.get("changed_at", ""), reverse=True)
    merged = merged[:per_page]

    total = profile_total + content_total
    pagination = _paginate(page, per_page, total)

    # Collect unique field names and user names for filter dropdowns
    field_facets = profile_coll.distinct("field", {"prop_id": prop_id})
    user_facets = profile_coll.distinct("changed_by", {"prop_id": prop_id})

    return {
        "data": merged,
        "pagination": pagination,
        "filters": {
            "fields": sorted(field_facets),
            "users": sorted(user_facets),
        },
    }


def get_change_detail(prop_id: int, change_id: str) -> dict[str, Any] | None:
    """Return the full detail of a single change record (profile or content)."""
    from bson.objectid import ObjectId

    db: Database = get_database()
    try:
        oid = ObjectId(change_id)
    except Exception:
        return None

    # Try profile changes first
    doc = db.hotel_profile_changes.find_one({"_id": oid, "prop_id": prop_id})
    if doc is None:
        # Fallback to content changes
        doc = db.hotel_content_changes.find_one({"_id": oid, "prop_id": prop_id})

    if doc is None:
        return None

    changed_at = doc.get("changed_at")
    return {
        "id": str(doc["_id"]),
        "prop_id": doc.get("prop_id"),
        "field": doc.get("field", ""),
        "old_value": doc.get("old_value", ""),
        "new_value": doc.get("new_value", ""),
        "changed_by": doc.get("changed_by", ""),
        "changed_at": changed_at.isoformat() if hasattr(changed_at, "isoformat") else str(changed_at or ""),
        "source": doc.get("source", ""),
        "reason": doc.get("reason", ""),
        "entity_type": doc.get("entity_type", "profile"),
    }
