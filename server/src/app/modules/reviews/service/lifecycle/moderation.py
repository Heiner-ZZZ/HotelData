"""Review moderation and staff response operations."""

from __future__ import annotations

import logging

from bson import ObjectId
from pymongo import ReturnDocument

from src.database.connection import get_database
from ...schemas import ReviewModeration, ReviewStaffResponse
from ._helpers import _enrich, _notify_async, _now, _update_both

logger = logging.getLogger(__name__)

COLLECTION = "reviews"
FACT_COLLECTION = "fact_reviews"


def _notify_review_moderated(review_id, status, prop_id, guest_name):
    from src.app.modules.reviews.service.notifications import notify_review_moderated

    notify_review_moderated(
        review_id=review_id, status=status,
        prop_id=prop_id, guest_name=guest_name,
    )


def moderate_review(review_id: str, payload: ReviewModeration, current_user: dict | None = None) -> dict | None:
    db = get_database()
    if payload.status not in ("approved", "rejected"):
        return None
    doc_id = ObjectId(review_id)
    existing = db[COLLECTION].find_one({"_id": doc_id})
    if not existing:
        return None

    current_status = existing.get("moderation_status")
    if current_status in ("approved", "rejected"):
        return None

    moderated_by = None
    if current_user:
        moderated_by = current_user.get("username") or current_user.get("email", str(current_user.get("_id", "")))

    update_fields = {"moderation_status": payload.status, "updated_at": _now()}
    if moderated_by:
        update_fields["moderated_by"] = moderated_by
        update_fields["moderated_at"] = _now()
    if payload.reason:
        update_fields["moderation_reason"] = payload.reason

    doc = db[COLLECTION].find_one_and_update(
        {"_id": doc_id}, {"$set": update_fields}, return_document=ReturnDocument.AFTER,
    )
    if doc:
        _update_both(COLLECTION, FACT_COLLECTION, doc_id, {"$set": update_fields})
        result = _enrich(doc)
        _notify_async(
            _notify_review_moderated,
            review_id=result["id"], status=payload.status,
            prop_id=result.get("prop_id", 0), guest_name=result.get("user_display_name", "Huésped"),
        )
        return result
    return None


def respond_to_review(review_id: str, payload: ReviewStaffResponse) -> dict | None:
    db = get_database()
    doc_id = ObjectId(review_id)
    existing = db[COLLECTION].find_one({"_id": doc_id})
    if not existing:
        return None
    if existing.get("moderation_status") != "approved":
        return None

    doc = db[COLLECTION].find_one_and_update(
        {"_id": doc_id},
        {"$set": {"staff_response": payload.response, "staff_response_at": _now(), "updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        _update_both(COLLECTION, FACT_COLLECTION, doc_id, {
            "$set": {"staff_response": payload.response, "staff_response_at": _now(), "updated_at": _now()},
        })
    return _enrich(doc) if doc else None
