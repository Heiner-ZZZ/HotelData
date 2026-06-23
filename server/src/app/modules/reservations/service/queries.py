from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, DESCENDING

from src.app.security.hotel_filter import hotel_filter_from_user
from src.database.connection import get_database
from src.app.modules.hotels.service import hotel_detail
from src.app.modules.partner.services import partner_hotel_detail


def hotel_booking_context(prop_id: int) -> dict[str, Any]:
    detail = hotel_detail(prop_id)
    if detail:
        return {
            "prop_id": prop_id,
            "hotel_label": detail.get("hotel_label") or f"Hotel {prop_id}",
            "country": detail.get("prop_country_id"),
            "review_label": detail.get("review_label"),
            "avg_price_label": detail.get("avg_price_label"),
        }
    partner = partner_hotel_detail(prop_id)
    if partner:
        hotel = partner["hotel"]
        return {
            "prop_id": prop_id,
            "hotel_label": hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {prop_id}",
            "country": hotel.get("prop_country_id"),
            "review_label": hotel.get("review_score_label"),
            "avg_price_label": partner["performance"].get("avg_price_label"),
        }
    return {"prop_id": prop_id, "hotel_label": f"Hotel {prop_id}", "country": None, "review_label": "N/D", "avg_price_label": "N/D"}


def list_bookings(page: int = 1, page_size: int = 20, created_date: str | None = None, user: dict[str, Any] | None = None) -> dict[str, Any]:
    db = get_database()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 20)
    filters: dict[str, Any] = {}
    user_filter = hotel_filter_from_user(user)
    if user_filter:
        filters.update(user_filter)
    if created_date:
        filters["$expr"] = {"$eq": [{"$substr": ["$created_at", 0, 10]}, created_date]}
    total = db.booking_orders.count_documents(filters)
    total_pages = (total + page_size - 1) // page_size if total else 0
    if total_pages and page > total_pages:
        page = total_pages
    items = list(
        db.booking_orders.find(filters, {"_id": 0})
        .sort([("created_at", DESCENDING)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    contexts = {item["booking_id"]: hotel_booking_context(int(item["prop_id"])) for item in items if item.get("prop_id") is not None}
    for item in items:
        item["hotel"] = contexts.get(item["booking_id"])
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1 and total_pages > 0,
        "has_next": total_pages > 0 and page < total_pages,
    }


def list_reservation_dates(*, prop_id: int | None = None, user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return distinct created_at dates with booking count, optionally filtered by property."""
    db = get_database()
    filters: dict[str, Any] = {}
    user_filter = hotel_filter_from_user(user)
    if user_filter:
        filters.update(user_filter)
    if prop_id:
        filters["prop_id"] = prop_id
    # created_at is stored as ISO string, use $substr to extract date part
    pipeline: list[dict[str, Any]] = [
        {"$match": filters},
        {"$group": {
            "_id": {"$substr": ["$created_at", 0, 10]},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": -1}},
        {"$project": {"_id": 0, "date": "$_id", "count": 1}},
    ]
    return list(db.booking_orders.aggregate(pipeline))


def get_booking_detail(booking_id: str) -> dict[str, Any] | None:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0})
    if booking is None:
        return None
    guest = db.booking_guests.find_one({"booking_id": booking_id, "is_primary": True}, {"_id": 0})
    history = list(db.booking_status_history.find({"booking_id": booking_id}, {"_id": 0}).sort([("changed_at", ASCENDING)]))
    manual = db.manual_reservations.find_one({"booking_id": booking_id}, {"_id": 0})
    return {
        "booking": booking,
        "guest": guest,
        "history": history,
        "manual": manual,
        "hotel": hotel_booking_context(int(booking["prop_id"])) if booking.get("prop_id") is not None else None,
        "can_cancel": booking.get("status") == "requested",
    }
