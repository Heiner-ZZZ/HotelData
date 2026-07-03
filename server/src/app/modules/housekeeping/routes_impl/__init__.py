"""Housekeeping routes implementation — inline logic extracted from route handlers."""

from __future__ import annotations

from fastapi import HTTPException, status

from src.database.connection import get_database


# ── Room Status helpers ──


def validate_bulk_update(payload: dict) -> tuple[int, list[str], str, str]:
    """Extract and validate bulk room status update params."""
    prop_id = payload.get("prop_id")
    room_labels = payload.get("room_labels", [])
    new_status = payload.get("status", "available")
    note = payload.get("note", "")
    if not prop_id or not room_labels:
        raise HTTPException(status_code=400, detail="prop_id y room_labels son requeridos")
    return prop_id, room_labels, new_status, note


def validate_sync_payload(payload: dict) -> int:
    """Extract and validate sync payload."""
    prop_id = payload.get("prop_id")
    if not prop_id:
        raise HTTPException(status_code=400, detail="prop_id es requerido")
    return prop_id


# ── Cleaning helpers ──


def extract_cleaning_start_params(payload: dict) -> tuple[int, str, str, str | None]:
    """Extract and validate cleaning start parameters."""
    prop_id = int(payload.get("prop_id", 0))
    room_label = payload.get("room_label", "")
    if not prop_id or not room_label:
        raise HTTPException(status_code=400, detail="prop_id y room_label son requeridos")
    return prop_id, room_label, payload.get("assigned_to", ""), payload.get("task_id")


def extract_cleaning_complete_params(payload: dict) -> dict:
    """Extract and validate cleaning complete parameters."""
    prop_id = int(payload.get("prop_id", 0))
    room_label = payload.get("room_label", "")
    if not prop_id or not room_label:
        raise HTTPException(status_code=400, detail="prop_id y room_label son requeridos")
    return {
        "prop_id": prop_id,
        "room_label": room_label,
        "assigned_to": payload.get("assigned_to", ""),
        "observations": payload.get("observations", ""),
        "damage_found": bool(payload.get("damage_found", False)),
        "damage_description": payload.get("damage_description", ""),
        "lost_object_found": bool(payload.get("lost_object_found", False)),
        "lost_object_description": payload.get("lost_object_description", ""),
        "needs_maintenance": bool(payload.get("needs_maintenance", False)),
        "maintenance_description": payload.get("maintenance_description", ""),
    }


def extract_cleaning_approve_params(payload: dict) -> tuple[int, str, str, str, bool]:
    """Extract and validate cleaning approve parameters."""
    prop_id = int(payload.get("prop_id", 0))
    room_label = payload.get("room_label", "")
    if not prop_id or not room_label:
        raise HTTPException(status_code=400, detail="prop_id y room_label son requeridos")
    return (
        prop_id,
        room_label,
        payload.get("inspected_by", "supervisor"),
        payload.get("note", ""),
        bool(payload.get("set_occupied", False)),
    )


# ── Staff users query ──


def query_housekeeping_staff(prop_id: int | None = None) -> list[dict]:
    """Query staff users with maintenance/housekeeping roles."""
    db = get_database()
    roles = ["maintenance", "housekeeping"]
    query: dict = {"primary_role": {"$in": roles}, "is_active": True}
    if prop_id:
        query["assigned_hotels"] = prop_id
    return list(
        db.users.find(
            query,
            {"_id": 0, "username": 1, "display_name": 1, "email": 1, "primary_role": 1, "assigned_hotels": 1},
        ).sort("display_name", 1)
    )
