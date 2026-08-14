"""Explicitly privileged repairs for reconciliation findings.

The read-only report (``service.py``) deliberately never writes; repairs live
here and are only reachable through their own POST endpoint.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.database.connection import get_database

from .service import find_phantom_occupied_rooms
from src.app.modules.housekeeping.service.collections import ROOM_STATUS_COLLECTION
from src.app.modules.housekeeping.service.lifecycle.room_history import log_room_status_change

_REPAIR_NOTE = "Reconciliación: ocupada fantasma revertida a vacante"


def repair_phantom_occupied_rooms(prop_id: int) -> dict[str, Any]:
    """Revert phantom ``occupied_clean`` room_status_log rows to ``vacant_clean``.

    Idempotent: a room is only touched when it is occupied_clean and no
    checked-in stay references it, so genuine occupancy and non-occupied
    statuses are never modified. Every reverted room is logged to
    ``room_status_history`` for the audit trail.
    """
    db = get_database()
    phantom = find_phantom_occupied_rooms(db, prop_id)
    now = datetime.now(timezone.utc).isoformat()

    reverted: list[str] = []
    for doc in phantom:
        room_label = doc.get("room_label")
        result = db[ROOM_STATUS_COLLECTION].update_one(
            {"prop_id": prop_id, "room_label": room_label},
            {"$set": {"status": "vacant_clean", "note": _REPAIR_NOTE, "updated_at": now}},
        )
        if result.matched_count:
            reverted.append(str(room_label))
            log_room_status_change(
                prop_id=prop_id,
                room_label=str(room_label),
                old_status="occupied_clean",
                new_status="vacant_clean",
                note=_REPAIR_NOTE,
                changed_by="reconciliation:repair",
            )

    return {"prop_id": int(prop_id), "reverted": reverted, "count": len(reverted)}
