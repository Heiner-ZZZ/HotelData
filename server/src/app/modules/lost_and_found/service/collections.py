from __future__ import annotations
from typing import TYPE_CHECKING

from pymongo import ASCENDING, DESCENDING, IndexModel

from src.database.collections import ensure_collection

if TYPE_CHECKING:
    from src.app.modules.lost_and_found.schemas import ModuleStatus

LOST_AND_FOUND_COLLECTION = "lost_and_found"

LOST_AND_FOUND_INDEXES = [
    IndexModel([("prop_id", ASCENDING)], name="idx_lf_prop"),
    IndexModel([("status", ASCENDING)], name="idx_lf_status"),
    IndexModel([("booking_id", ASCENDING)], name="idx_lf_booking"),
    IndexModel([("created_at", DESCENDING)], name="idx_lf_created"),
    IndexModel([("prop_id", ASCENDING), ("status", ASCENDING)], name="idx_lf_prop_status"),
]


def ensure_lost_and_found_collections() -> None:
    ensure_collection(LOST_AND_FOUND_COLLECTION, LOST_AND_FOUND_INDEXES)


def module_status() -> ModuleStatus:
    from src.app.modules.lost_and_found.schemas import ModuleStatus
    return ModuleStatus(
        module="lost_and_found",
        status="active",
        description="Registro de objetos olvidados por huéspedes con trazabilidad de devolución.",
    )
