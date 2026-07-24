"""Review editing operations (author-only, while pending)."""

from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from src.database.connection import get_database
from ...schemas import ReviewUpdate
from ._helpers import _enrich, _now, _update_both

logger = logging.getLogger(__name__)

COLLECTION = "reviews"
FACT_COLLECTION = "fact_reviews"


def update_review(
    review_id: str,
    user_id: str,
    payload: ReviewUpdate,
) -> dict | None:
    """Update a review if the user is the author and the review is still pending moderation."""
    db = get_database()
    try:
        doc_id = ObjectId(review_id)
    except InvalidId:
        logger.warning("Invalid review_id for update: %s", review_id)
        return None

    # Fetch existing review
    existing = db[COLLECTION].find_one({"_id": doc_id})
    if not existing:
        return None

    # Ownership check: must be the author
    if str(existing.get("user_id", "")) != user_id:
        return None

    # Only allow editing while pending
    if existing.get("moderation_status") != "pending":
        return None

    # Build update fields — only provided fields
    set_fields: dict[str, Any] = {"updated_at": _now()}
    if payload.rating is not None:
        set_fields["rating"] = payload.rating
    if payload.title is not None:
        set_fields["title"] = payload.title
    if payload.comment is not None:
        set_fields["comment"] = payload.comment

    # Re-analyze sentiment if rating, title, or comment changed
    if payload.rating is not None or payload.title is not None or payload.comment is not None:
        try:
            from src.app.ai.sentiment import analyze_review_sentiment
            rating = payload.rating if payload.rating is not None else existing.get("rating", 3)
            title = payload.title if payload.title is not None else existing.get("title", "")
            comment = payload.comment if payload.comment is not None else existing.get("comment", "")
            sentiment = analyze_review_sentiment(rating, title, comment)
            set_fields["sentiment_label"] = sentiment["sentiment_label"]
            set_fields["sentiment_score"] = sentiment["sentiment_score"]
            set_fields["sentiment_confidence"] = sentiment["confidence"]
            set_fields["sentiment_analyzed_at"] = _now().isoformat()
        except Exception:
            logger.exception("Failed to re-analyze sentiment for review %s", review_id)

    doc = db[COLLECTION].find_one_and_update(
        {"_id": doc_id},
        {"$set": set_fields},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        _update_both(COLLECTION, FACT_COLLECTION, doc_id, {"$set": set_fields})

    return _enrich(doc) if doc else None
