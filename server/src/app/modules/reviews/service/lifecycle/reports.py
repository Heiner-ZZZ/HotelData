"""Review report operations (report inappropriate reviews)."""

from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId

from src.database.connection import get_database
from ..collections import REPORTS_COLLECTION
from ...schemas import ReviewReportCreate
from ._helpers import _now

logger = logging.getLogger(__name__)

COLLECTION = "reviews"

REPORT_STATUSES = {"pending", "reviewed", "dismissed"}


def _fmt(val):
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if val else None


def _enrich_report(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    doc["review_id"] = str(doc.get("review_id", ""))
    doc["reported_by"] = str(doc.get("reported_by", ""))
    if "created_at" in doc:
        doc["created_at"] = _fmt(doc["created_at"])
    return doc


def create_review_report(
    review_id: str,
    user_id: str,
    payload: ReviewReportCreate,
) -> dict | None:
    """Report a review for inappropriate content.

    Validates that the review exists and that the user hasn't already reported it.
    """
    db = get_database()
    try:
        review_oid = ObjectId(review_id)
    except Exception:
        return None

    # Verify review exists
    review = db[COLLECTION].find_one({"_id": review_oid}, {"_id": 1})
    if not review:
        return None

    # Prevent duplicate reports from the same user
    existing = db[REPORTS_COLLECTION].find_one({
        "review_id": review_oid,
        "reported_by": ObjectId(user_id),
    })
    if existing:
        return None

    now = _now()
    doc = {
        "review_id": review_oid,
        "reported_by": ObjectId(user_id),
        "reason": payload.reason,
        "description": payload.description,
        "status": "pending",
        "created_at": now,
    }
    result = db[REPORTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    # Log an audit entry
    try:
        db.booking_status_history.insert_one({
            "booking_id": review_id,
            "status": "review_reported",
            "changed_at": now,
            "reason": f"Reseña reportada: {payload.reason}",
            "changed_by": str(user_id),
            "is_test": False,
        })
    except Exception:
        logger.exception("Failed to log report audit for review %s", review_id)

    return _enrich_report(doc)


def list_review_reports(
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List review reports (for moderation staff)."""
    from math import ceil

    db = get_database()
    query: dict[str, Any] = {}
    if status and status in REPORT_STATUSES:
        query["status"] = status

    total = db[REPORTS_COLLECTION].count_documents(query)
    cursor = (
        db[REPORTS_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_report(doc) for doc in cursor]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)) if total else 1,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }
