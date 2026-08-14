from __future__ import annotations

from pymongo import ASCENDING, DESCENDING, IndexModel

from src.database.collections import ensure_collection

RECEPTION_SHIFTS_COLLECTION = "reception_shifts"

RECEPTION_SHIFT_CONFIG_COLLECTION = "reception_shift_config"

RECEPTION_SHIFTS_INDEXES = [
    IndexModel([("prop_id", ASCENDING), ("status", ASCENDING)], name="idx_rs_prop_status"),
    IndexModel([("prop_id", ASCENDING), ("start_time", DESCENDING)], name="idx_rs_prop_start"),
    IndexModel([("hotel_id", ASCENDING), ("status", ASCENDING), ("closed_at", DESCENDING)], name="idx_rs_hotel_status_closed"),
    IndexModel([("shift_type", ASCENDING)], name="idx_rs_type"),
]

# One config doc per property (unique prop_id).
RECEPTION_SHIFT_CONFIG_INDEXES = [
    IndexModel([("prop_id", ASCENDING)], name="idx_rsc_prop", unique=True),
]

# Dedup markers for internal shift notifications: one row per
# (shift_id, notification_type) so the periodic sweep never double-notifies.
SHIFT_NOTIFICATION_DEDUP_COLLECTION = "shift_notification_dedup"
SHIFT_NOTIFICATION_DEDUP_INDEXES = [
    IndexModel(
        [("shift_id", ASCENDING), ("notification_type", ASCENDING)],
        name="idx_snd_shift_type",
        unique=True,
    ),
]


def ensure_reception_collections() -> None:
    ensure_collection(RECEPTION_SHIFTS_COLLECTION, RECEPTION_SHIFTS_INDEXES)
    ensure_collection(RECEPTION_SHIFT_CONFIG_COLLECTION, RECEPTION_SHIFT_CONFIG_INDEXES)
    ensure_collection(SHIFT_NOTIFICATION_DEDUP_COLLECTION, SHIFT_NOTIFICATION_DEDUP_INDEXES)
