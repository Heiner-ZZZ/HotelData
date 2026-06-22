from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ReturnDocument

from src.database.connection import get_database
from src.app.modules.reviews.schemas import ReviewCreate, ReviewModeration, ReviewStaffResponse

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


def create_review(user_id: str, payload: ReviewCreate) -> dict | None:
    db = get_database()
    booking = db.booking_orders.find_one({"_id": ObjectId(payload.booking_id)})
    if not booking:
        return None
    if booking.get("user_id") != ObjectId(user_id):
        return None
    existing = db[COLLECTION].find_one({"booking_id": payload.booking_id})
    if existing:
        return None

    doc = {
        "booking_id": ObjectId(payload.booking_id),
        "prop_id": payload.prop_id,
        "user_id": ObjectId(user_id),
        "rating": payload.rating,
        "title": payload.title,
        "comment": payload.comment,
        "moderation_status": "pending",
        "staff_response": None,
        "staff_response_at": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    _write_both(COLLECTION, FACT_COLLECTION, doc)
    return _enrich(doc)


def list_reviews(
    prop_id: int | None = None,
    user_id: str | None = None,
    moderation_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    db = get_database()
    query: dict = {}
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
    return _enrich(doc) if doc else None


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
        return
    db = get_database()
    user = db.users.find_one({"_id": ObjectId(doc["user_id"])}, {"display_name": 1, "username": 1})
    doc["user_display_name"] = (user or {}).get("display_name") or (user or {}).get("username", "")
