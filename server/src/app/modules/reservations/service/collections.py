from __future__ import annotations

from typing import Any

from pymongo import IndexModel, ASCENDING, DESCENDING

from src.database.collections import ensure_collection

# TTL: 90 days in seconds
NOTIFICATION_LOG_TTL_SECONDS = 90 * 24 * 60 * 60

BOOKING_COLLECTIONS: dict[str, list[IndexModel]] = {
    "booking_orders": [
        IndexModel([("booking_id", ASCENDING)], name="booking_id_1", unique=True),
        IndexModel([("user_id", ASCENDING)], name="user_id_1"),
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("status", ASCENDING)], name="status_1"),
        IndexModel([("created_at", DESCENDING)], name="created_at_-1"),
    ],
    "booking_guests": [
        IndexModel([("booking_id", ASCENDING)], name="booking_id_1"),
    ],
    "booking_room_guests": [
        IndexModel([("booking_id", ASCENDING)], name="booking_id_1"),
        IndexModel([("booking_id", ASCENDING), ("room_index", ASCENDING)], name="booking_id_room_idx", unique=True),
    ],
    "booking_status_history": [
        IndexModel([("booking_id", ASCENDING)], name="booking_id_1"),
        IndexModel([("changed_at", DESCENDING)], name="changed_at_-1"),
    ],
    "manual_reservations": [
        IndexModel([("manual_reservation_id", ASCENDING)], name="manual_reservation_id_1", unique=True),
        IndexModel([("booking_id", ASCENDING)], name="booking_id_1"),
        IndexModel([("prop_id", ASCENDING)], name="prop_id_1"),
        IndexModel([("created_at", DESCENDING)], name="created_at_-1"),
    ],
    "notification_log": [
        IndexModel([("booking_id", ASCENDING)], name="idx_notif_booking"),
        IndexModel([("notification_type", ASCENDING)], name="idx_notif_type"),
        IndexModel([("status", ASCENDING)], name="idx_notif_status"),
        IndexModel([("created_at", ASCENDING)], name="idx_notif_ttl", expireAfterSeconds=NOTIFICATION_LOG_TTL_SECONDS),
    ],
}


def ensure_reservation_collections() -> dict[str, Any]:
    created: list[str] = []
    for name, indexes in BOOKING_COLLECTIONS.items():
        created.extend(ensure_collection(name, indexes))
    return {"collections": list(BOOKING_COLLECTIONS), "created": created}
