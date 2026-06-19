from __future__ import annotations

from typing import Any

from pymongo import DESCENDING

from src.database.connection import get_database


def ensure_reservation_collections() -> dict[str, Any]:
    db = get_database()
    db.booking_orders.create_index("booking_id", unique=True)
    db.booking_orders.create_index("user_id")
    db.booking_orders.create_index("prop_id")
    db.booking_orders.create_index("status")
    db.booking_orders.create_index([("created_at", DESCENDING)])
    db.booking_guests.create_index("booking_id")
    db.booking_status_history.create_index("booking_id")
    db.booking_status_history.create_index([("changed_at", DESCENDING)])
    db.manual_reservations.create_index("manual_reservation_id", unique=True)
    db.manual_reservations.create_index("booking_id")
    db.manual_reservations.create_index("prop_id")
    db.manual_reservations.create_index([("created_at", DESCENDING)])
    return {
        "collections": [
            "booking_orders",
            "booking_guests",
            "booking_status_history",
            "manual_reservations",
        ],
    }
