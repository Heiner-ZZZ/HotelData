"""Review query and list operations."""

from __future__ import annotations

import logging

from bson import ObjectId
from bson.errors import InvalidId

from src.database.connection import get_database

logger = logging.getLogger(__name__)
from ._helpers import _enrich

COLLECTION = "reviews"


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
    if hotel_filter:
        query.update(hotel_filter)
    if prop_id:
        query["prop_id"] = prop_id
    if user_id:
        try:
            query["user_id"] = ObjectId(user_id)
        except InvalidId:
            logger.warning("Invalid user_id received: %s", user_id)
    if moderation_status:
        query["moderation_status"] = moderation_status

    total = db[COLLECTION].count_documents(query)
    cursor = db[COLLECTION].find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    items = [_enrich(doc) for doc in cursor]
    return {
        "items": items, "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
        "has_next": page * page_size < total, "has_prev": page > 1,
    }


def get_review(review_id: str) -> dict | None:
    db = get_database()
    try:
        oid = ObjectId(review_id)
    except InvalidId:
        logger.warning("Invalid review_id received: %s", review_id)
        return None
    doc = db[COLLECTION].find_one({"_id": oid})
    return _enrich(doc) if doc else None


def get_hotel_reviews(prop_id: int, page: int = 1, page_size: int = 5) -> dict:
    db = get_database()
    query = {"prop_id": prop_id, "moderation_status": "approved"}
    total = db[COLLECTION].count_documents(query)
    cursor = (
        db[COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [_enrich(doc) for doc in cursor],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def delete_review(review_id: str) -> bool:
    db = get_database()
    try:
        oid = ObjectId(review_id)
    except InvalidId:
        logger.warning("Invalid review_id for delete: %s", review_id)
        return False
    result = db[COLLECTION].delete_one({"_id": oid})
    return result.deleted_count > 0
