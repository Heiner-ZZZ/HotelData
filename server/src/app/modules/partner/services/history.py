"""History / audit-log queries for partner properties.

Provides paginated listing and detail lookup for changes recorded in
`hotel_profile_changes` (profile edits) and `hotel_content_changes`
(content edits). Both collections are written automatically by the
respective save functions — this module only reads them.

Note (Fase 5 reports migration): this service returns raw Mongo
documents (``_id`` as ObjectId, ``changed_at`` as datetime). The Pydantic
``*Response`` models in ``routes/hotels.py`` own the wire-shape contract
— they coerce ObjectId → str via ``ObjectIdStr`` and serialize datetime
as ISO 8601 automatically. Don't pre-format here.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
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

    Returns raw Mongo documents (with ``_id`` as ObjectId and
    ``changed_at`` as datetime) — wire-shape coercion happens in the
    Pydantic ``PropertyHistoryListResponse`` model in ``routes/hotels.py``.
    Supports filtering by date range, field, user (changed_by), and source.
    Results are sorted by changed_at descending (most recent first).
    """
    db: Database = get_database()
    page = max(page, 1)
    per_page = min(max(per_page, 1), 200)

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

    profile_coll: Collection = db.hotel_profile_changes
    content_coll: Collection = db.hotel_content_changes

    profile_total = profile_coll.count_documents(base_filter)
    content_total = content_coll.count_documents({**base_filter, "entity_type": {"$exists": True}})

    # Fetch RAW docs (no normalization). Pydantic owns serialization.
    profile_docs = list(
        profile_coll
        .find(base_filter, {"_id": 1, "field": 1, "old_value": 1, "new_value": 1,
                            "changed_by": 1, "changed_at": 1, "source": 1, "reason": 1})
        .sort([("changed_at", -1)])
        .skip((page - 1) * per_page)
        .limit(per_page)
    )

    content_docs = list(
        content_coll
        .find({**base_filter, "entity_type": {"$exists": True}},
              {"_id": 1, "field": 1, "old_value": 1, "new_value": 1,
               "changed_by": 1, "changed_at": 1, "source": 1, "reason": 1})
        .sort([("changed_at", -1)])
        .limit(per_page)
    )

    # OPT-A: sort by datetime objects directly (previously string ISO).
    # Robust to None (legacy rows that lack changed_at); they sort last.
    merged = sorted(
        profile_docs + content_docs,
        key=lambda d: d.get("changed_at") or datetime.min,
        reverse=True,
    )
    merged = merged[:per_page]

    total = profile_total + content_total
    pagination = _paginate(page, per_page, total)

    field_facets = sorted(profile_coll.distinct("field", {"prop_id": prop_id}))
    user_facets = sorted(profile_coll.distinct("changed_by", {"prop_id": prop_id}))

    return {
        "data": merged,
        "pagination": pagination,
        "filters": {
            "fields": field_facets,
            "users": user_facets,
        },
    }


def get_change_detail(prop_id: int, change_id: str) -> dict[str, Any] | None:
    """Return the full detail of a SINGLE change record.

    Returns the raw Mongo document (``_id`` as ObjectId, ``changed_at`` as
    datetime) when found, or ``None`` to trigger a 404 in the route.
    Document is enriched with ``entity_type`` defaulting to "profile"
    so the wire response carries an explicit discriminator.
    """
    db: Database = get_database()
    try:
        oid = ObjectId(change_id)
    except Exception:
        return None

    # Try profile changes first
    doc = db.hotel_profile_changes.find_one({"_id": oid, "prop_id": prop_id})
    source_collection = "profile"
    if doc is None:
        # Fallback to content changes
        doc = db.hotel_content_changes.find_one({"_id": oid, "prop_id": prop_id})
        source_collection = "content"

    if doc is None:
        return None

    # The Mongo doc may lack entity_type (profile docs). Set the
    # discriminator so the wire response carries it explicitly.
    doc.setdefault("entity_type", source_collection)
    return doc
