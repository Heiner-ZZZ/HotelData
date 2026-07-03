"""Review report operations (report inappropriate reviews) and reputation dashboard."""

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


def get_reputation_dashboard(
    prop_id: int | None = None,
    days: int = 30,
) -> dict:
    """Return reputation dashboard data: GRI, departmental sentiment, recent feedback, and trends."""
    from datetime import datetime, timedelta, timezone
    from math import ceil

    db = get_database()
    since = datetime.now(timezone.utc) - timedelta(days=days)

    query: dict = {"created_at": {"$gte": since}, "moderation_status": "approved"}
    if prop_id:
        query["prop_id"] = prop_id

    cursor = db[COLLECTION].find(query).sort("created_at", -1)
    reviews = list(cursor)

    total = len(reviews)
    if total == 0:
        return {
            "gri": 0,
            "gri_target": 90.0,
            "gri_change": 0,
            "total_reviews": 0,
            "departmental": [],
            "recent_feedback": [],
            "daily_counts": [],
        }

    # Global Review Index
    avg_rating = sum(r.get("rating", 0) for r in reviews) / total
    gri = round((avg_rating / 5) * 100, 1)

    # Departmental sentiment from service_ratings
    dept_data: dict[str, list[int]] = {"housekeeping": [], "food_beverage": [], "staff": []}
    for r in reviews:
        sr = r.get("service_ratings") or {}
        for dept in dept_data:
            val = sr.get(dept)
            if val is not None:
                dept_data[dept].append(val)

    dept_labels = {
        "housekeeping": "Housekeeping",
        "food_beverage": "F&B",
        "staff": "Staff",
    }
    dept_icons = {
        "housekeeping": "cleaning_services",
        "food_beverage": "restaurant",
        "staff": "concierge",
    }
    departmental = []
    for dept, ratings in dept_data.items():
        if ratings:
            avg = sum(ratings) / len(ratings)
            pct = round((avg / 5) * 100)
            positive = sum(1 for r in ratings if r >= 4)
            neutral = sum(1 for r in ratings if r == 3)
            negative = sum(1 for r in ratings if r <= 2)
            total_r = len(ratings)
            departmental.append({
                "key": dept,
                "label": dept_labels.get(dept, dept),
                "icon": dept_icons.get(dept, "star"),
                "score": pct,
                "positive_pct": round(positive / total_r * 100),
                "neutral_pct": round(neutral / total_r * 100),
                "negative_pct": round(negative / total_r * 100),
                "total_ratings": total_r,
            })

    # Recent feedback (last 10)
    recent = []
    for r in reviews[:10]:
        recent.append({
            "id": str(r["_id"]),
            "user_name": r.get("user_display_name", "Huésped"),
            "rating": r.get("rating", 0),
            "comment": (r.get("comment") or "")[:150],
            "created_at": r.get("created_at").isoformat() if hasattr(r.get("created_at"), "isoformat") else str(r.get("created_at", "")),
        })

    # Daily counts for trend chart
    from collections import Counter
    day_counts: Counter = Counter()
    for r in reviews:
        dt = r.get("created_at")
        if hasattr(dt, "strftime"):
            day_counts[dt.strftime("%Y-%m-%d")] += 1
    daily_counts = [{"date": d, "count": c} for d, c in sorted(day_counts.items())]

    # GRI change (compare first half vs second half of period)
    gri_change = 0
    if len(reviews) >= 4:
        mid = len(reviews) // 2
        first_half = [r.get("rating", 0) for r in reviews[mid:]]
        second_half = [r.get("rating", 0) for r in reviews[:mid]]
        if first_half and second_half:
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            gri_change = round(((avg_second - avg_first) / 5) * 100, 1)

    return {
        "gri": gri,
        "gri_target": 90.0,
        "gri_change": gri_change,
        "total_reviews": total,
        "departmental": departmental,
        "recent_feedback": recent,
        "daily_counts": daily_counts,
    }


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
