"""Guest listing for hotel management — aggregate guest data from booking_orders.

Returns minimal PII (name, email) with booking stats per guest, scoped by property.
Super-admin sees all properties; hotel managers see only their own.
"""

from __future__ import annotations

from typing import Any

from src.database.connection import get_database


def list_guests_for_prop(
    prop_id: int,
    *,
    q: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Return paginated guest list for a property, deduplicated by guest_email.

    Args:
        prop_id: Property ID to scope results.
        q: Optional search query (matches guest_name or guest_email).
        page: 1-based page number.
        page_size: Items per page (max 100).

    Returns:
        dict with keys: items, total, page, page_size, has_next
    """
    db = get_database()

    match: dict[str, Any] = {"prop_id": prop_id, "guest_email": {"$ne": "", "$exists": True}}

    if q:
        q_clean = q.strip()
        if q_clean:
            import re as _re
            escaped = _re.escape(q_clean)
            match["$or"] = [
                {"guest_name": {"$regex": escaped, "$options": "i"}},
                {"guest_email": {"$regex": escaped, "$options": "i"}},
            ]

    pipeline: list[dict[str, Any]] = [
        {"$match": match},
        {
            "$group": {
                "_id": "$guest_email",
                "guest_name": {"$last": "$guest_name"},
                "guest_email": {"$last": "$guest_email"},
                "guest_phone": {"$last": "$guest_phone"},
                "total_bookings": {"$sum": 1},
                "last_booking_date": {"$max": "$check_in_date"},
                "total_spent": {"$sum": {"$ifNull": ["$total_price", 0]}},
                "last_status": {"$last": "$status"},
            },
        },
        {"$sort": {"last_booking_date": -1, "guest_name": 1}},
    ]

    # Count total distinct guests
    count_pipeline = pipeline + [{"$count": "total"}]
    count_result = list(db.booking_orders.aggregate(count_pipeline))
    total = count_result[0]["total"] if count_result else 0

    # Paginate
    skip = (page - 1) * page_size
    items = list(
        db.booking_orders.aggregate(
            pipeline + [{"$skip": skip}, {"$limit": page_size}]
        )
    )

    guests = []
    for item in items:
        guests.append({
            "guest_name": item.get("guest_name", ""),
            "guest_email": item.get("guest_email", ""),
            "guest_phone": item.get("guest_phone", ""),
            "total_bookings": item.get("total_bookings", 0),
            "last_booking_date": item.get("last_booking_date", ""),
            "total_spent": round(item.get("total_spent", 0), 2),
            "last_status": item.get("last_status", ""),
        })

    return {
        "items": guests,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": (skip + page_size) < total,
    }
