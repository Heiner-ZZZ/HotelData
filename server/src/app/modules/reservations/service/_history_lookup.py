from __future__ import annotations

from typing import Any

from src.database.connection import get_database


def _booking_history_lookup(booking_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not booking_ids:
        return {}
    db = get_database()
    items = list(
        db.booking_status_history.find({"booking_id": {"$in": booking_ids}}, {"_id": 0})
        .sort([("changed_at", ASCENDING)])
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(item["booking_id"], []).append(item)
    return grouped


def _guest_lookup(booking_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not booking_ids:
        return {}
    db = get_database()
    guests = list(
        db.booking_guests.find(
            {"booking_id": {"$in": booking_ids}, "is_primary": True},
            {"_id": 0},
        )
    )
    return {item["booking_id"]: item for item in guests}


def _derived_stay_status(booking: dict[str, Any], history: list[dict[str, Any]], *, flow: str) -> str:
    explicit = str(booking.get("stay_status") or "").strip().lower()
    if explicit:
        return explicit
    statuses = [str(item.get("status") or "").strip().lower() for item in history]
    if "checked_out" in statuses:
        return "checked_out"
    if "checked_in" in statuses:
        return "checked_in"
    if booking.get("status") == "cancelled":
        return "cancelled"
    if booking.get("status") == "rejected":
        return "no_show" if flow == "check_in" else "cancelled"
    return "pending"


def _reservation_status_label(status: str) -> str:
    mapping = {
        "pending": "Pendiente",
        "confirmed": "Confirmada",
        "cancelled": "Cancelada",
        "rejected": "Rechazada",
        "checked_in": "Check-in completado",
        "checked_out": "Check-out completado",
        "pending": "Pendiente",
        "no_show": "No-show",
    }
    return mapping.get(status, status or "Pendiente")
