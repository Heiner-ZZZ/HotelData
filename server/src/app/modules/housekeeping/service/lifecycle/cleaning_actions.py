"""Housekeeper cleaning actions — el formulario que la camarera usa durante la limpieza.

Flujo:
  cleaning_in_progress  → (hora inicio, asignación)
  cleaning_completed    → (hora fin, observaciones, fotos, daños, objetos)
  Si daño encontrado    → maintenance_requested + bloqueo automático
  Si objeto encontrado  → lost_and_found entry
"""

from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId

from src.database.connection import get_database
from ..collections import ROOM_STATUS_COLLECTION, HOUSEKEEPING_COLLECTION
from ...schemas import now_iso

logger = logging.getLogger(__name__)

# ── Cleaning Session Management ──


def start_cleaning(
    prop_id: int,
    room_label: str,
    *,
    assigned_to: str = "",
    task_id: str | None = None,
) -> dict[str, Any] | None:
    """Mark a room as cleaning_in_progress and create/update the housekeeping task.

    Records the start time and sets the room status to cleaning_in_progress.
    """
    db = get_database()
    now = now_iso()

    # 1. Update room status to cleaning_in_progress
    old_status = _get_room_status(db, prop_id, room_label)
    db[ROOM_STATUS_COLLECTION].update_one(
        {"prop_id": prop_id, "room_label": room_label},
        {
            "$set": {
                "status": "cleaning_in_progress",
                "note": f"Limpieza iniciada por {assigned_to or 'no asignado'}",
                "updated_at": now,
                "cleaning_started_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    _log_status_change(prop_id, room_label, old_status, "cleaning_in_progress", assigned_to)

    # 2. Create or update the housekeeping task
    if task_id:
        db[HOUSEKEEPING_COLLECTION].find_one_and_update(
            {"_id": ObjectId(task_id)},
            {
                "$set": {
                    "status": "in_progress",
                    "assigned_to": assigned_to,
                    "started_at": now,
                    "updated_at": now,
                }
            },
        )
    else:
        task_doc = {
            "prop_id": prop_id,
            "room_label": room_label,
            "task_type": "cleaning",
            "status": "in_progress",
            "assigned_to": assigned_to,
            "priority": "normal",
            "note": "",
            "scheduled_date": "",
            "started_at": now,
            "created_at": now,
            "completed_at": None,
        }
        db[HOUSEKEEPING_COLLECTION].insert_one(task_doc)

    # Refresh and return
    doc = db[ROOM_STATUS_COLLECTION].find_one(
        {"prop_id": prop_id, "room_label": room_label}
    )
    return _enrich_rs(doc) if doc else None


def complete_cleaning(
    prop_id: int,
    room_label: str,
    *,
    assigned_to: str = "",
    observations: str = "",
    damage_found: bool = False,
    damage_description: str = "",
    lost_object_found: bool = False,
    lost_object_description: str = "",
    needs_maintenance: bool = False,
    maintenance_description: str = "",
) -> dict[str, Any]:
    """Complete a cleaning task with the housekeeper's report.

    Transitions the room to:
    - cleaning_completed (if no damage/major issues)
    - maintenance_requested (if damage found or maintenance needed)

    Auto-creates maintenance tickets and Lost & Found entries as needed.
    """
    db = get_database()
    now = now_iso()
    old_status = _get_room_status(db, prop_id, room_label)

    # ── Determine next status ──
    if damage_found or needs_maintenance:
        new_status = "maintenance_requested"
        note_parts = []
        if damage_found:
            note_parts.append(f"Daño: {damage_description}")
        if needs_maintenance:
            note_parts.append(f"Mtto: {maintenance_description}")
        note = " | ".join(note_parts) or "Mantenimiento requerido"

        # Auto-create maintenance task
        _auto_create_maintenance(
            db, prop_id, room_label,
            damage_found=damage_found,
            damage_description=damage_description,
            needs_maintenance=needs_maintenance,
            maintenance_description=maintenance_description,
        )
    else:
        new_status = "cleaning_completed"
        note = observations or "Limpieza completada"

    # Update room status
    update: dict[str, Any] = {
        "status": new_status,
        "note": note,
        "updated_at": now,
        "cleaning_completed_at": now,
        "cleaning_observations": observations,
    }
    if damage_found:
        update["damage_found"] = True
        update["damage_description"] = damage_description
    if lost_object_found:
        update["lost_object_found"] = True
        update["lost_object_description"] = lost_object_description

    db[ROOM_STATUS_COLLECTION].update_one(
        {"prop_id": prop_id, "room_label": room_label},
        {"$set": update},
    )
    _log_status_change(prop_id, room_label, old_status, new_status, assigned_to, note)

    # ── Auto-create Lost & Found entry ──
    if lost_object_found and lost_object_description:
        try:
            db.lost_and_found_items.insert_one({
                "prop_id": prop_id,
                "room_label": room_label,
                "item_description": lost_object_description,
                "found_by": assigned_to or "housekeeper",
                "found_at": now,
                "status": "pending",
                "created_at": now,
            })
            logger.info(
                "Lost & found entry created for room %s (prop %s): %s",
                room_label, prop_id, lost_object_description,
            )
        except Exception:
            logger.exception("Failed to create lost & found entry for room %s", room_label)

    # Mark the housekeeping task as completed
    db[HOUSEKEEPING_COLLECTION].update_many(
        {
            "prop_id": prop_id,
            "room_label": room_label,
            "status": "in_progress",
        },
        {
            "$set": {
                "status": "completed" if new_status == "cleaning_completed" else "blocked",
                "completed_at": now,
                "observations": observations,
                "damage_found": damage_found,
                "damage_description": damage_description,
                "lost_object_found": lost_object_found,
                "lost_object_description": lost_object_description,
                "updated_at": now,
            }
        },
    )

    doc = db[ROOM_STATUS_COLLECTION].find_one(
        {"prop_id": prop_id, "room_label": room_label}
    )
    return _enrich_rs(doc) if doc else {"ok": True, "status": new_status}


# ── Auto-maintenance ──


def _auto_create_maintenance(
    db: Any,
    prop_id: int,
    room_label: str,
    *,
    damage_found: bool = False,
    damage_description: str = "",
    needs_maintenance: bool = False,
    maintenance_description: str = "",
) -> None:
    """Create a maintenance task and block the room automatically."""
    from src.app.modules.housekeeping.service.lifecycle.maintenance import create_maintenance_task
    from src.app.modules.housekeeping.schemas import MaintenanceTaskCreate

    # Build description from damage + maintenance info
    desc_parts = []
    task_type = "corrective"
    if damage_found:
        desc_parts.append(f"Daño reportado: {damage_description}")
    if needs_maintenance:
        desc_parts.append(f"Mantenimiento requerido: {maintenance_description}")
        task_type = "preventive"

    title = f"{'Daño' if damage_found else 'Mtto'} — Hab. {room_label}"

    try:
        room = db.hotel_rooms.find_one(
            {"prop_id": prop_id, "room_label": room_label},
            {"hotel_room_id": 1},
        )
        if not room or not room.get("hotel_room_id"):
            raise ValueError(f"Habitación no encontrada para mantenimiento automático: {room_label}")
        create_maintenance_task(MaintenanceTaskCreate(
            prop_id=prop_id,
            room_id=room["hotel_room_id"],
            task_type=task_type,
            title=title,
            description=" | ".join(desc_parts) if desc_parts else "Reportado automáticamente desde limpieza",
            priority="high" if damage_found else "normal",
            status="scheduled",
            auto_block=True,
        ))
        logger.info(
            "Auto-maintenance created for room %s (prop %s): %s",
            room_label, prop_id, title,
        )
    except Exception:
        logger.exception("Failed to auto-create maintenance for room %s", room_label)


# ── Approval Flow ──


def approve_cleaning(
    prop_id: int,
    room_label: str,
    *,
    inspected_by: str = "supervisor",
    note: str = "",
    set_occupied: bool = False,
) -> dict[str, Any] | None:
    """Supervisor approves the cleaning → room becomes vacant_clean or occupied_clean."""
    db = get_database()
    now = now_iso()
    old_status = _get_room_status(db, prop_id, room_label)
    new_status = "occupied_clean" if set_occupied else "vacant_clean"

    db[ROOM_STATUS_COLLECTION].update_one(
        {"prop_id": prop_id, "room_label": room_label},
        {
            "$set": {
                "status": new_status,
                "note": note or f"Aprobado por {inspected_by}",
                "updated_at": now,
                "inspected_by": inspected_by,
                "inspected_at": now,
                "cleaning_completed_at": None,
                "cleaning_started_at": None,
            }
        },
    )
    _log_status_change(prop_id, room_label, old_status, new_status, inspected_by, note)

    doc = db[ROOM_STATUS_COLLECTION].find_one(
        {"prop_id": prop_id, "room_label": room_label}
    )
    return _enrich_rs(doc) if doc else None


# ── Helpers ──


def _get_room_status(db: Any, prop_id: int, room_label: str) -> str | None:
    existing = db[ROOM_STATUS_COLLECTION].find_one(
        {"prop_id": prop_id, "room_label": room_label},
        {"_id": 0, "status": 1},
    )
    return existing.get("status") if existing else None


def _log_status_change(
    prop_id: int,
    room_label: str,
    old_status: str | None,
    new_status: str,
    changed_by: str = "system",
    note: str = "",
) -> None:
    from .room_history import log_room_status_change
    try:
        log_room_status_change(
            prop_id=prop_id,
            room_label=room_label,
            old_status=old_status or "",
            new_status=new_status,
            note=note or "",
            changed_by=changed_by or "system",
        )
    except Exception:
        logger.exception("Failed to log status change for %s", room_label)


def _enrich_rs(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at", "updated_at", "cleaning_started_at", "cleaning_completed_at"):
        if f in doc and hasattr(doc[f], "isoformat"):
            doc[f] = doc[f].isoformat()
    doc["roomLabel"] = doc.get("room_label", "")
    doc["propId"] = doc.get("prop_id", 0)
    doc["roomTypeId"] = doc.get("room_type_id", "")
    doc["hotelRoomId"] = doc.get("hotel_room_id", "")
    return doc
