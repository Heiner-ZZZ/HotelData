from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, DESCENDING

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


def get_reservation_stats() -> dict[str, Any]:
    """Return counts of bookings grouped by status."""
    db = get_database()
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    raw = list(db.booking_orders.aggregate(pipeline))
    stats: dict[str, int] = {"total": 0}
    for entry in raw:
        status_key = str(entry["_id"]) if entry["_id"] else "unknown"
        stats[status_key] = int(entry["count"])
        stats["total"] += int(entry["count"])
    # Ensure all statuses are represented (even if 0)
    for s in ("pending", "confirmed", "cancelled", "rejected", "checked_in", "checked_out"):
        stats.setdefault(s, 0)
    stats["active"] = stats.get("pending", 0) + stats.get("confirmed", 0) + stats.get("checked_in", 0)
    stats["completed"] = stats.get("checked_out", 0)
    stats["lost"] = stats.get("cancelled", 0) + stats.get("rejected", 0)
    return stats


def list_bookings(
    page: int = 1,
    page_size: int = 20,
    *,
    status: str | None = None,
    prop_id: int | None = None,
    guest_name: str | None = None,
    guest_email: str | None = None,
    check_in_from: str | None = None,
    check_in_to: str | None = None,
) -> dict[str, Any]:
    db = get_database()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 20)

    # Build dynamic filter
    filter_dict: dict[str, Any] = {}
    if status:
        filter_dict["status"] = status
    if prop_id:
        filter_dict["prop_id"] = prop_id
    if guest_name:
        filter_dict["guest_name"] = {"$regex": guest_name, "$options": "i"}
    if guest_email:
        filter_dict["guest_email"] = {"$regex": guest_email, "$options": "i"}
    if check_in_from or check_in_to:
        date_filter: dict[str, str] = {}
        if check_in_from:
            date_filter["$gte"] = check_in_from
        if check_in_to:
            date_filter["$lte"] = check_in_to
        filter_dict["check_in_date"] = date_filter

    total = db.booking_orders.count_documents(filter_dict)
    total_pages = (total + page_size - 1) // page_size if total else 0
    if total_pages and page > total_pages:
        page = total_pages
    items = list(
        db.booking_orders.find(filter_dict, {"_id": 0})
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


def get_booking_detail(booking_id: str) -> dict[str, Any] | None:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0})
    if booking is None:
        return None
    guest = db.booking_guests.find_one({"booking_id": booking_id, "is_primary": True}, {"_id": 0})
    history = list(db.booking_status_history.find({"booking_id": booking_id}, {"_id": 0}).sort([("changed_at", ASCENDING)]))
    manual = db.manual_reservations.find_one({"booking_id": booking_id}, {"_id": 0})
    total_price = booking.get("total_price")
    return {
        "booking": booking,
        "guest": guest,
        "history": history,
        "manual": manual,
        "hotel": hotel_booking_context(int(booking["prop_id"])) if booking.get("prop_id") is not None else None,
        "can_cancel": booking.get("status") == "pending",
        "total_price": total_price,
        "total_price_label": f"${total_price:.2f}" if total_price is not None else None,
        "currency": booking.get("currency", "USD"),
        "total_nights": booking.get("total_nights", 0),
    }
