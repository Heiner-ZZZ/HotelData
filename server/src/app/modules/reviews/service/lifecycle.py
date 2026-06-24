from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument

from src.database.connection import get_database
from src.app.ai.sentiment import analyze_review_sentiment
from src.app.modules.reviews.schemas import ReviewCreate, ReviewModeration, ReviewStaffResponse
from src.app.modules.reviews.service.notifications import notify_review_created, notify_review_moderated

logger = logging.getLogger(__name__)

COLLECTION = "reviews"
FACT_COLLECTION = "fact_reviews"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _write_both(collection: str, fact_collection: str, doc: dict) -> ObjectId:
    db = get_database()
    result = db[collection].insert_one(doc)
    fact_doc = {**doc, "operational_id": result.inserted_id}
    db[fact_collection].insert_one(fact_doc)
    doc["_id"] = result.inserted_id
    return result.inserted_id


def _update_both(collection: str, fact_collection: str, doc_id: ObjectId, update: dict) -> None:
    db = get_database()
    db[collection].update_one({"_id": doc_id}, update)
    db[fact_collection].update_one({"_id": doc_id}, update)


def _validate_booking(payload: ReviewCreate) -> tuple[dict, ObjectId, str] | None:
    """Validate a booking exists and isn't already reviewed.

    Returns (booking_doc, user_id_obj, user_id_str) or None if invalid.
    """
    db = get_database()
    booking = db.booking_orders.find_one({"_id": ObjectId(payload.booking_id)})
    if not booking:
        return None
    existing = db[COLLECTION].find_one({"booking_id": payload.booking_id})
    if existing:
        return None
    user_id_obj = booking.get("user_id")
    if not user_id_obj:
        return None
    return booking, user_id_obj, str(user_id_obj)


def create_review(user_id: str, payload: ReviewCreate) -> dict | None:
    """Create a review as the guest themselves (user_id must match booking)."""
    validated = _validate_booking(payload)
    if not validated:
        return None
    booking, user_id_obj, _ = validated
    if booking.get("user_id") != ObjectId(user_id):
        return None

    sentiment = analyze_review_sentiment(payload.rating, payload.title, payload.comment)
    doc = {
        "booking_id": ObjectId(payload.booking_id),
        "prop_id": payload.prop_id,
        "user_id": user_id_obj,
        "rating": payload.rating,
        "title": payload.title,
        "comment": payload.comment,
        "moderation_status": "pending",
        "staff_response": None,
        "staff_response_at": None,
        "created_at": _now(),
        "updated_at": _now(),
        "sentiment_label": sentiment["sentiment_label"],
        "sentiment_score": sentiment["sentiment_score"],
        "sentiment_confidence": sentiment["confidence"],
        "sentiment_analyzed_at": _now().isoformat(),
    }
    _write_both(COLLECTION, FACT_COLLECTION, doc)
    result = _enrich(doc)
    # Notify staff about the new review
    _notify_async(
        notify_review_created,
        prop_id=payload.prop_id,
        review_id=result["id"],
        rating=payload.rating,
        title=payload.title,
        comment=payload.comment,
        guest_name=result.get("user_display_name", "Huésped"),
    )
    return result



def create_review_staff(payload: ReviewCreate) -> dict | None:
    """Create a review on behalf of a guest (staff-assisted, e.g. during check-out).

    Resolves the guest's user_id from the booking automatically.
    No user_id match check — the staff user is acting on behalf of the guest.
    """
    validated = _validate_booking(payload)
    if not validated:
        return None
    _, user_id_obj, _ = validated

    sentiment = analyze_review_sentiment(payload.rating, payload.title, payload.comment)
    doc = {
        "booking_id": ObjectId(payload.booking_id),
        "prop_id": payload.prop_id,
        "user_id": user_id_obj,
        "rating": payload.rating,
        "title": payload.title,
        "comment": payload.comment,
        "moderation_status": "pending",
        "staff_response": None,
        "staff_response_at": None,
        "created_at": _now(),
        "updated_at": _now(),
        "sentiment_label": sentiment["sentiment_label"],
        "sentiment_score": sentiment["sentiment_score"],
        "sentiment_confidence": sentiment["confidence"],
        "sentiment_analyzed_at": _now().isoformat(),
    }
    _write_both(COLLECTION, FACT_COLLECTION, doc)
    result = _enrich(doc)
    # Notify staff about the new review
    _notify_async(
        notify_review_created,
        prop_id=payload.prop_id,
        review_id=result["id"],
        rating=payload.rating,
        title=payload.title,
        comment=payload.comment,
        guest_name=result.get("user_display_name", "Huésped"),
    )
    return result


def create_review_guest(payload: ReviewCreate) -> dict | None:
    """Create a review as an unauthenticated guest."""
    validated = _validate_booking(payload)
    if not validated:
        return None
    _, user_id_obj, _ = validated

    sentiment = analyze_review_sentiment(payload.rating, payload.title, payload.comment)
    doc = {
        "booking_id": ObjectId(payload.booking_id),
        "prop_id": payload.prop_id,
        "user_id": user_id_obj,
        "rating": payload.rating,
        "title": payload.title,
        "comment": payload.comment,
        "moderation_status": "pending",
        "staff_response": None,
        "staff_response_at": None,
        "created_at": _now(),
        "updated_at": _now(),
        "sentiment_label": sentiment["sentiment_label"],
        "sentiment_score": sentiment["sentiment_score"],
        "sentiment_confidence": sentiment["confidence"],
        "sentiment_analyzed_at": _now().isoformat(),
    }
    _write_both(COLLECTION, FACT_COLLECTION, doc)
    result = _enrich(doc)
    # Notify staff about the new review
    _notify_async(
        notify_review_created,
        prop_id=payload.prop_id,
        review_id=result["id"],
        rating=payload.rating,
        title=payload.title,
        comment=payload.comment,
        guest_name=result.get("user_display_name", "Huésped"),
    )
    return result


def list_reviews(
    hotel_filter: dict | None = None,
    prop_id: int | None = None,
    user_id: str | None = None,
    moderation_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    db = get_database()
    query: dict = {}
    # Apply RBAC hotel filter (restricts to assigned hotels for hotel_partner/gerente_hotel)
    if hotel_filter:
        query.update(hotel_filter)
    if prop_id:
        query["prop_id"] = prop_id
    if user_id:
        query["user_id"] = ObjectId(user_id)
    if moderation_status:
        query["moderation_status"] = moderation_status

    total = db[COLLECTION].count_documents(query)
    cursor = (
        db[COLLECTION]
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
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def get_review(review_id: str) -> dict | None:
    db = get_database()
    doc = db[COLLECTION].find_one({"_id": ObjectId(review_id)})
    return _enrich(doc) if doc else None


def moderate_review(review_id: str, payload: ReviewModeration) -> dict | None:
    db = get_database()
    if payload.status not in ("approved", "rejected"):
        return None
    doc_id = ObjectId(review_id)
    doc = db[COLLECTION].find_one_and_update(
        {"_id": doc_id},
        {"$set": {"moderation_status": payload.status, "updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        _update_both(COLLECTION, FACT_COLLECTION, doc_id, {"$set": {"moderation_status": payload.status, "updated_at": _now()}})
        result = _enrich(doc)
        # Notify guest about moderation result
        _notify_async(
            notify_review_moderated,
            review_id=result["id"],
            status=payload.status,
            prop_id=result.get("prop_id", 0),
            guest_name=result.get("user_display_name", "Huésped"),
        )
        return result
    return None


def respond_to_review(review_id: str, payload: ReviewStaffResponse) -> dict | None:
    db = get_database()
    doc_id = ObjectId(review_id)
    doc = db[COLLECTION].find_one_and_update(
        {"_id": doc_id},
        {
            "$set": {
                "staff_response": payload.response,
                "staff_response_at": _now(),
                "updated_at": _now(),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        _update_both(COLLECTION, FACT_COLLECTION, doc_id, {
            "$set": {
                "staff_response": payload.response,
                "staff_response_at": _now(),
                "updated_at": _now(),
            }
        })
    return _enrich(doc) if doc else None


def delete_review(review_id: str) -> bool:
    db = get_database()
    result = db[COLLECTION].delete_one({"_id": ObjectId(review_id)})
    return result.deleted_count > 0


def _enrich(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id", doc.get("_id", "")))
    doc["booking_id"] = str(doc.get("booking_id", ""))
    doc["user_id"] = str(doc.get("user_id", ""))
    for field in ("created_at", "updated_at", "staff_response_at"):
        val = doc.get(field)
        if isinstance(val, datetime):
            doc[field] = val.isoformat()
    _add_user_name(doc)
    return doc


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
    """Execute a notification function, catching all exceptions so the caller never fails."""
    try:
        func(**kwargs)
    except Exception:
        logger.exception("Notification failed for review: %s", kwargs.get("review_id", "?"))
