from __future__ import annotations

from pymongo import ASCENDING, IndexModel

from src.database.collections import drop_index_safe, ensure_collection

ROOM_STATUS_COLLECTION = "room_status_log"
HOUSEKEEPING_COLLECTION = "housekeeping_tasks"
MAINTENANCE_COLLECTION = "maintenance_tasks"
CHARGES_COLLECTION = "additional_charges"

ROOM_STATUS_INDEXES = [
    IndexModel([("prop_id", ASCENDING)], name="idx_rs_prop"),
    IndexModel([("room_label", ASCENDING)], name="idx_rs_room"),
    IndexModel([("status", ASCENDING)], name="idx_rs_status"),
    IndexModel([("prop_id", ASCENDING), ("hotel_room_id", ASCENDING)], name="idx_rs_prop_room", unique=True),
]

HOUSEKEEPING_INDEXES = [
    IndexModel([("prop_id", ASCENDING)], name="idx_hk_prop"),
    IndexModel([("status", ASCENDING)], name="idx_hk_status"),
    IndexModel([("assigned_to", ASCENDING)], name="idx_hk_assigned"),
    IndexModel([("created_at", ASCENDING)], name="idx_hk_created"),
]

MAINTENANCE_INDEXES = [
    IndexModel([("prop_id", ASCENDING)], name="idx_mt_prop"),
    IndexModel([("status", ASCENDING)], name="idx_mt_status"),
    IndexModel([("scheduled_date", ASCENDING)], name="idx_mt_scheduled"),
]

CHARGES_INDEXES = [
    IndexModel([("booking_id", ASCENDING)], name="idx_ch_booking"),
    IndexModel([("prop_id", ASCENDING)], name="idx_ch_prop"),
    IndexModel([("created_at", ASCENDING)], name="idx_ch_created"),
]


def ensure_housekeeping_collections() -> None:
    # Drop old unique index on (prop_id, room_label) — replaced by (prop_id, hotel_room_id)
    drop_index_safe(ROOM_STATUS_COLLECTION, "idx_rs_prop_room")
    ensure_collection(ROOM_STATUS_COLLECTION, ROOM_STATUS_INDEXES)
    ensure_collection(HOUSEKEEPING_COLLECTION, HOUSEKEEPING_INDEXES)
    ensure_collection(MAINTENANCE_COLLECTION, MAINTENANCE_INDEXES)
    ensure_collection(CHARGES_COLLECTION, CHARGES_INDEXES)


def module_status() -> ModuleStatus:
    from src.app.modules.housekeeping.schemas import ModuleStatus
    return ModuleStatus(
        module="housekeeping",
        status="active",
        description="Gestión de housekeeping, mantenimiento y cargos adicionales (CU-O30 a CU-O40).",
    )
