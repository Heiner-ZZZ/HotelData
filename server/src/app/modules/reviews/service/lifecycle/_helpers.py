"""Shared helpers for reviews lifecycle package."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from bson import ObjectId

from src.database.connection import get_database
from src.app.core.outbox import write_with_outbox, update_with_outbox

logger = logging.getLogger(__name__)

COLLECTION = "reviews"
FACT_COLLECTION = "fact_reviews"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _write_both(collection: str, fact_collection: str, doc: dict) -> ObjectId:
    db = get_database()
    return write_with_outbox(db, collection, doc, fact_collection)


def _update_both(collection: str, fact_collection: str, doc_id: ObjectId, update: dict) -> None:
    db = get_database()
    update_with_outbox(db, collection, doc_id, update, fact_collection)


def _enrich(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id", doc.get("_id", "")))
    doc["booking_id"] = str(doc.get("booking_id", ""))
    doc["user_id"] = str(doc.get("user_id", ""))
    for field in ("created_at", "updated_at", "staff_response_at"):
        val = doc.get(field)
        if isinstance(val, datetime):
            doc[field] = val.isoformat()
    _add_user_name(doc)
    _add_hotel_label(doc)
    return doc


def _add_hotel_label(doc: dict) -> None:
    """Resolve ``prop_id`` → human hotel name for detail views.

    Uses ``dim_hotels.display_name`` → ``hotel_name`` → fallback ``Hotel {prop_id}``,
    same as ``src.app.core.resolvers.resolve_hotel_name`` but inline to avoid
    circular import and to keep _enrich self-contained. Never fails the request:
    on any error keeps ``hotel_label`` as ``Hotel {prop_id}``.
    """
    prop_id = doc.get("prop_id")
    if prop_id is None:
        doc["hotel_label"] = ""
        return
    try:
        db = get_database()
        hotel = db.dim_hotels.find_one(
            {"prop_id": int(prop_id)},
            {"display_name": 1, "hotel_name": 1, "_id": 0},
        )
        if hotel:
            doc["hotel_label"] = hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {prop_id}"
        else:
            doc["hotel_label"] = f"Hotel {prop_id}"
    except Exception:
        doc["hotel_label"] = f"Hotel {prop_id}"


def _add_user_name(doc: dict) -> None:
    if not doc.get("user_id"):
        doc["user_display_name"] = "Huésped"
        return
    try:
        db = get_database()
        user = db.users.find_one({"_id": ObjectId(doc["user_id"])}, {"display_name": 1, "username": 1})
        doc["user_display_name"] = (user or {}).get("display_name") or (user or {}).get("username", "Huésped")
    except Exception:
        doc["user_display_name"] = "Huésped"


def _notify_async(func, **kwargs) -> None:
    try:
        func(**kwargs)
    except Exception:
        logger.exception("Notification failed for review: %s", kwargs.get("review_id", "?"))
