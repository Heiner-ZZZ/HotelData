"""Review creation operations."""

from __future__ import annotations

import logging

from bson import ObjectId

from src.database.connection import get_database
from ...schemas import ReviewCreate
from ._helpers import _enrich, _notify_async, _now, _write_both

logger = logging.getLogger(__name__)

COLLECTION = "reviews"
FACT_COLLECTION = "fact_reviews"


def _validate_booking(payload: ReviewCreate) -> tuple[dict, ObjectId, str] | None:
    db = get_database()
    # Search by business booking_id string, not by MongoDB _id
    booking = db.booking_orders.find_one({"booking_id": payload.booking_id})
    if not booking:
        return None
    if booking.get("status") != "checked_out":
        return None
    existing = db[COLLECTION].find_one({"booking_id": payload.booking_id})
    if existing:
        return None
    user_id_obj = booking.get("user_id")
    if not user_id_obj:
        return None
    return booking, user_id_obj, str(user_id_obj)


def _build_review_doc(payload, user_id_obj, sentiment):
    doc = {
        "booking_id": payload.booking_id,
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
    if payload.service_ratings:
        doc["service_ratings"] = {
            "housekeeping": payload.service_ratings.housekeeping,
            "food_beverage": payload.service_ratings.food_beverage,
            "staff": payload.service_ratings.staff,
        }
    return doc


def _notify_review_created(prop_id, review_id, rating, title, comment, guest_name):
    from src.app.modules.reviews.service.notifications import notify_review_created

    notify_review_created(
        prop_id=prop_id, review_id=review_id, rating=rating,
        title=title, comment=comment, guest_name=guest_name,
    )


def create_review(user_id: str, payload: ReviewCreate) -> dict | None:
    validated = _validate_booking(payload)
    if not validated:
        return None
    booking, user_id_obj, _ = validated
    if booking.get("user_id") != ObjectId(user_id):
        return None

    from src.app.ai.sentiment import analyze_review_sentiment

    sentiment = analyze_review_sentiment(payload.rating, payload.title, payload.comment)
    doc = _build_review_doc(payload, user_id_obj, sentiment)
    _write_both(COLLECTION, FACT_COLLECTION, doc)
    result = _enrich(doc)
    _notify_async(
        _notify_review_created,
        prop_id=payload.prop_id, review_id=result["id"], rating=payload.rating,
        title=payload.title, comment=payload.comment, guest_name=result.get("user_display_name", "Huésped"),
    )
    return result


def create_review_staff(payload: ReviewCreate) -> dict | None:
    validated = _validate_booking(payload)
    if not validated:
        return None
    _, user_id_obj, _ = validated

    from src.app.ai.sentiment import analyze_review_sentiment

    sentiment = analyze_review_sentiment(payload.rating, payload.title, payload.comment)
    doc = _build_review_doc(payload, user_id_obj, sentiment)
    _write_both(COLLECTION, FACT_COLLECTION, doc)
    result = _enrich(doc)
    _notify_async(
        _notify_review_created,
        prop_id=payload.prop_id, review_id=result["id"], rating=payload.rating,
        title=payload.title, comment=payload.comment, guest_name=result.get("user_display_name", "Huésped"),
    )
    return result


def create_review_guest(payload: ReviewCreate) -> dict | None:
    validated = _validate_booking(payload)
    if not validated:
        return None
    _, user_id_obj, _ = validated

    from src.app.ai.sentiment import analyze_review_sentiment

    sentiment = analyze_review_sentiment(payload.rating, payload.title, payload.comment)
    doc = _build_review_doc(payload, user_id_obj, sentiment)
    _write_both(COLLECTION, FACT_COLLECTION, doc)
    result = _enrich(doc)
    _notify_async(
        _notify_review_created,
        prop_id=payload.prop_id, review_id=result["id"], rating=payload.rating,
        title=payload.title, comment=payload.comment, guest_name=result.get("user_display_name", "Huésped"),
    )
    return result
