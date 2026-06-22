from __future__ import annotations

from typing import Any

from pymongo import IndexModel, ASCENDING, DESCENDING

from src.database.collections import ensure_collection

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
}


def ensure_reservation_collections() -> dict[str, Any]:
    created: list[str] = []
    for name, indexes in BOOKING_COLLECTIONS.items():
        created.extend(ensure_collection(name, indexes))
    return {"collections": list(BOOKING_COLLECTIONS), "created": created}
