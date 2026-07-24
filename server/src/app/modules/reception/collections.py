from __future__ import annotations

from pymongo import ASCENDING, DESCENDING, IndexModel

from src.database.collections import ensure_collection

RECEPTION_SHIFTS_COLLECTION = "reception_shifts"

RECEPTION_SHIFTS_INDEXES = [
    IndexModel([("prop_id", ASCENDING), ("status", ASCENDING)], name="idx_rs_prop_status"),
    IndexModel([("prop_id", ASCENDING), ("start_time", DESCENDING)], name="idx_rs_prop_start"),
    IndexModel([("hotel_id", ASCENDING), ("status", ASCENDING), ("closed_at", DESCENDING)], name="idx_rs_hotel_status_closed"),
    IndexModel([("shift_type", ASCENDING)], name="idx_rs_type"),
]


def ensure_reception_collections() -> None:
    ensure_collection(RECEPTION_SHIFTS_COLLECTION, RECEPTION_SHIFTS_INDEXES)
