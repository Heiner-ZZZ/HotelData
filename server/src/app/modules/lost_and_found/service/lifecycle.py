from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId

from src.app.core.resolvers import resolve_hotel_id, resolve_employee_id
from src.database.connection import get_database

from ..schemas import LostItemCreate, LostItemUpdate, now_iso
from .collections import LOST_AND_FOUND_COLLECTION

logger = logging.getLogger(__name__)


def _enrich(doc: dict[str, Any]) -> dict[str, Any]:
    """Convert MongoDB document to API response shape."""
    doc["id"] = str(doc.pop("_id", ""))
    return doc


def create_lost_item(payload: LostItemCreate) -> dict[str, Any]:
    """Register a new lost & found item."""
    db = get_database()
    now = now_iso()

    # Resolve ObjectId FKs for referential integrity
    hotel_id = resolve_hotel_id(payload.prop_id)
    found_by_id = resolve_employee_id(payload.found_by) if payload.found_by else None

    doc = {
        "prop_id": payload.prop_id,
        "hotel_id": hotel_id,
        "booking_id": payload.booking_id or "",
        "guest_name": payload.guest_name or "",
        "guest_contact": payload.guest_contact or "",
        "item_name": payload.item_name.strip(),
        "description": payload.description.strip(),
        "found_location": payload.found_location.strip(),
        "found_by": payload.found_by.strip(),
        "found_by_id": found_by_id,
        "status": payload.status if payload.status in ("pending", "claimed", "disposed", "returned") else "pending",
        "notes": payload.notes.strip(),
        "returned_to": "",
        "returned_at": None,
        "created_at": now,
        "updated_at": now,
    }

    result = db[LOST_AND_FOUND_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _enrich(doc)


def get_lost_item(item_id: str) -> dict[str, Any] | None:
    """Get a single lost & found item by ID."""
    db = get_database()
    try:
        doc = db[LOST_AND_FOUND_COLLECTION].find_one({"_id": ObjectId(item_id)})
        return _enrich(doc) if doc else None
    except Exception:
        return None


def list_lost_items(
    prop_id: int | None = None,
    status_filter: str | None = None,
    booking_id: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List lost & found items with optional filters and pagination."""
    db = get_database()
    query: dict[str, Any] = {"status": {"$ne": "archived"}}

    if prop_id is not None:
        query["prop_id"] = prop_id
    if status_filter:
        query["status"] = status_filter
    if booking_id:
        query["booking_id"] = booking_id
    if search:
        import re
        pattern = re.compile(re.escape(search), re.IGNORECASE)
        query["$or"] = [
            {"item_name": pattern},
            {"description": pattern},
            {"guest_name": pattern},
            {"found_location": pattern},
        ]

    total = db[LOST_AND_FOUND_COLLECTION].count_documents(query)
    cursor = (
        db[LOST_AND_FOUND_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich(doc) for doc in cursor]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def update_lost_item(item_id: str, payload: LostItemUpdate) -> dict[str, Any] | None:
    """Update a lost & found item."""
    db = get_database()
    try:
        oid = ObjectId(item_id)
    except Exception:
        return None

    update: dict[str, Any] = {"updated_at": now_iso()}

    for field in ("item_name", "description", "found_location", "found_by", "notes", "guest_name", "guest_contact", "returned_to", "returned_at"):
        val = getattr(payload, field, None)
        if val is not None:
            update[field] = val.strip() if isinstance(val, str) else val

    if payload.status is not None:
        allowed = ("pending", "claimed", "disposed", "returned")
        update["status"] = payload.status if payload.status in allowed else "pending"

    doc = db[LOST_AND_FOUND_COLLECTION].find_one_and_update(
        {"_id": oid},
        {"$set": update},
        return_document=True,
    )
    return _enrich(doc) if doc else None


def delete_lost_item(item_id: str) -> dict[str, Any] | None:
    """Archive a lost-and-found item instead of physically deleting evidence."""
    db = get_database()
    try:
        now = now_iso()
        doc = db[LOST_AND_FOUND_COLLECTION].find_one_and_update(
            {"_id": ObjectId(item_id), "status": {"$ne": "archived"}},
            {"$set": {"status": "archived", "archived_at": now, "updated_at": now}},
            return_document=True,
        )
        return _enrich(doc) if doc else None
    except Exception:
        return None


def claim_lost_item(item_id: str, *, returned_to: str = "", notes: str = "") -> dict[str, Any] | None:
    """Mark a lost item as returned/claimed by the guest."""
    db = get_database()
    try:
        oid = ObjectId(item_id)
    except Exception:
        return None

    now = now_iso()
    update: dict[str, Any] = {
        "status": "returned",
        "returned_to": returned_to.strip(),
        "returned_at": now,
        "notes": notes.strip() if notes else "",
        "updated_at": now,
    }

    doc = db[LOST_AND_FOUND_COLLECTION].find_one_and_update(
        {"_id": oid},
        {"$set": update},
        return_document=True,
    )
    return _enrich(doc) if doc else None


def dispose_lost_item(item_id: str, *, notes: str = "") -> dict[str, Any] | None:
    """Mark a lost item as disposed (thrown away, donated, etc.)."""
    db = get_database()
    try:
        oid = ObjectId(item_id)
    except Exception:
        return None

    now = now_iso()
    update: dict[str, Any] = {
        "status": "disposed",
        "notes": notes.strip() if notes else "",
        "updated_at": now,
    }

    doc = db[LOST_AND_FOUND_COLLECTION].find_one_and_update(
        {"_id": oid},
        {"$set": update},
        return_document=True,
    )
    return _enrich(doc) if doc else None
