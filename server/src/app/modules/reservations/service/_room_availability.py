"""Real-time room availability validation for early check-in.

Provides a lightweight endpoint that the frontend calls when the early
check-in dialog opens, so the receptionist sees current room status before
authorizing the early arrival — not stale data from page load.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from src.app.core.state_machine import CHECKIN_ALLOWED_ROOM_STATUSES
from src.app.core.timezone import local_today
from src.database.connection import get_database

logger = logging.getLogger(__name__)


def validate_room_availability(booking_id: str) -> dict[str, Any]:
    """Return real-time room availability context for a booking.

    Checks:
    1. Room current status (vacant_clean, vacant_dirty, occupied, maintenance, etc.)
    2. Overlapping reservations on the same physical room
    3. Pending housekeeping/maintenance tasks
    4. Room assignment existence

    This is READ-ONLY — no state mutations.
    """
    db = get_database()

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "prop_id": 1, "assigned_rooms": 1, "check_in_date": 1,
         "check_out_date": 1, "stay_status": 1},
    )
    if not booking:
        raise ValueError("Reserva no encontrada.")

    prop_id = int(booking.get("prop_id", 0) or 0)
    assigned_rooms: list[str] = booking.get("assigned_rooms") or []
    check_in_date = booking.get("check_in_date", "")
    check_out_date = booking.get("check_out_date", "")

    rooms: list[dict[str, Any]] = []
    all_available = True
    issues: list[str] = []

    if not assigned_rooms:
        return {
            "booking_id": booking_id,
            "all_available": False,
            "rooms": [],
            "issues": ["No hay habitaciones asignadas a esta reserva."],
        }

    # Fetch room documents
    room_docs = list(
        db.hotel_rooms.find(
            {"hotel_room_id": {"$in": assigned_rooms}},
            {"_id": 0, "hotel_room_id": 1, "room_label": 1, "floor": 1,
             "room_type_id": 1},
        )
    )
    room_map = {r["hotel_room_id"]: r for r in room_docs}

    # Get current statuses
    labels = [r.get("room_label", "") for r in room_docs if r.get("room_label")]
    status_map: dict[str, str] = {}
    if labels:
        for doc in db.room_status_log.find(
            {"prop_id": prop_id, "room_label": {"$in": labels}},
            {"_id": 0, "room_label": 1, "status": 1},
        ):
            status_map[doc["room_label"]] = doc["status"]

    # Check for overlapping reservations on the same physical room
    overlapping: dict[str, list[dict[str, Any]]] = {}
    if labels and check_in_date and check_out_date:
        # Find other active bookings assigned to the same rooms that overlap
        # the date range [check_in_date, check_out_date]
        pipeline = [
            {"$match": {
                "prop_id": prop_id,
                "assigned_rooms": {"$in": assigned_rooms},
                "booking_id": {"$ne": booking_id},
                "status": {"$nin": ["cancelled", "rejected"]},
                "stay_status": {"$nin": ["checked_out", "no_show"]},
                "$or": [
                    # New booking starts during our stay
                    {"check_in_date": {"$gte": check_in_date, "$lt": check_out_date}},
                    # New booking ends during our stay
                    {"check_out_date": {"$gt": check_in_date, "$lte": check_out_date}},
                    # New booking encompasses our stay
                    {"check_in_date": {"$lte": check_in_date},
                     "check_out_date": {"$gte": check_out_date}},
                ],
            }},
            {"$project": {
                "_id": 0, "booking_id": 1, "guest_name": 1,
                "check_in_date": 1, "check_out_date": 1,
                "assigned_rooms": 1, "stay_status": 1,
            }},
        ]
        overlapping_docs = list(db.booking_orders.aggregate(pipeline))
        for odoc in overlapping_docs:
            for room_id in odoc.get("assigned_rooms", []):
                if room_id in assigned_rooms:
                    overlapping.setdefault(room_id, []).append({
                        "booking_id": odoc["booking_id"],
                        "guest_name": odoc.get("guest_name", ""),
                        "check_in_date": odoc.get("check_in_date", ""),
                        "check_out_date": odoc.get("check_out_date", ""),
                        "stay_status": odoc.get("stay_status", ""),
                    })

    # Check for pending housekeeping tasks (cleaning) — informational only.
    pending_tasks: dict[str, list[str]] = {}
    if labels:
        task_docs = list(db.housekeeping_tasks.find(
            {"prop_id": prop_id, "room_label": {"$in": labels},
             "status": {"$in": ["pending", "in_progress"]}},
            {"_id": 0, "room_label": 1, "task_type": 1},
        ))
        for tdoc in task_docs:
            pending_tasks.setdefault(tdoc["room_label"], []).append(
                tdoc.get("task_type", "unknown")
            )

    # Active maintenance work orders block check-in. A room can be vacant_clean
    # while still carrying an open maintenance task (auto_block off, or the
    # status flip hasn't happened yet) — the task itself is the source of truth.
    # ``TASK_STATES`` (state_machine) defines the canonical task lifecycle
    # (pending → in_progress → completed/cancelled); only non-terminal states
    # block. ``scheduled``/``inspection`` are not canonical task states.
    _MAINTENANCE_BLOCKING_STATUSES = {"pending", "in_progress"}
    maintenance_map: dict[str, list[str]] = {}
    if labels:
        maintenance_docs = list(db.maintenance_tasks.find(
            {"prop_id": prop_id, "room_label": {"$in": labels},
             "status": {"$in": list(_MAINTENANCE_BLOCKING_STATUSES)}},
            {"_id": 0, "room_label": 1, "title": 1, "task_type": 1},
        ))
        for mdoc in maintenance_docs:
            maintenance_map.setdefault(mdoc["room_label"], []).append(
                mdoc.get("title") or mdoc.get("task_type") or "mantenimiento"
            )

    # Build room availability details
    today_str = local_today()
    for h_id in assigned_rooms:
        doc = room_map.get(h_id, {})
        label = doc.get("room_label", "")
        status = status_map.get(label, "unknown")
        is_vacant = status in CHECKIN_ALLOWED_ROOM_STATUSES
        has_overlap = h_id in overlapping and len(overlapping[h_id]) > 0
        has_tasks = label in pending_tasks
        has_maintenance = label in maintenance_map

        room_info: dict[str, Any] = {
            "hotel_room_id": h_id,
            "room_label": label,
            "floor": doc.get("floor", ""),
            "status": status,
            "is_vacant": is_vacant,
            "available": is_vacant and not has_overlap and not has_maintenance,
        }

        if has_overlap:
            room_info["overlapping_bookings"] = overlapping[h_id]
            all_available = False
            for ov in overlapping[h_id]:
                issues.append(
                    f"Habitación {label}: ocupada por reserva {ov['booking_id']} "
                    f"({ov['guest_name']}) hasta {ov['check_out_date']}."
                )

        if has_maintenance:
            room_info["maintenance_tasks"] = maintenance_map[label]
            all_available = False
            for title in maintenance_map[label]:
                issues.append(
                    f"Habitación {label}: tiene una tarea de mantenimiento activa ({title})."
                )

        if has_tasks:
            room_info["pending_tasks"] = pending_tasks[label]
            # Cleaning tasks stay informational — room status governs cleaning.
            if not is_vacant:
                all_available = False

        if not is_vacant:
            all_available = False
            if not has_overlap and not has_maintenance:
                issues.append(
                    f"Habitación {label}: estado '{status}' — no disponible para check-in."
                )

        rooms.append(room_info)

    return {
        "booking_id": booking_id,
        "all_available": all_available,
        "rooms": rooms,
        "issues": issues,
        "validated_at": today_str,
    }
