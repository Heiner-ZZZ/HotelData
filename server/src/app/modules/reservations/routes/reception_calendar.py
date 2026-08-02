"""Reception calendar — visual occupancy bars for the recepción page."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query

from src.app.core.timezone import local_today, local_now
from src.app.security.dependencies import require_permission
from src.database.connection import get_database

_logger = logging.getLogger(__name__)


def _normalise_assigned_room_id(value: Any) -> str:
    """Resolve legacy string or enriched snapshot values to a room ID."""
    if isinstance(value, dict):
        value = value.get("hotel_room_id") or value.get("room_id") or value.get("id")
    return str(value or "").strip()


reception_calendar_router = APIRouter(
    prefix="/api/management/reception",
    tags=["reception-calendar-api"],
)


def _parse_time_fraction(time_str: str) -> float:
    """Convert 'HH:MM' to a 0.0–1.0 fraction of a 24-hour day.

    00:00 → 0.0, 12:00 → 0.5, 23:59 → ~1.0
    """
    if not time_str or ":" not in time_str:
        return 0.0
    try:
        parts = time_str.strip().split(":")
        hours = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
        return (hours * 60 + minutes) / (24 * 60)
    except (ValueError, IndexError):
        return 0.0


def _reservation_status_label(booking: dict, today_str: str) -> str:
    """Determine visual status: 'active', 'upcoming', or 'past'."""
    check_in = (booking.get("check_in_date") or "")[:10]
    check_out = (booking.get("check_out_date") or "")[:10]
    status = booking.get("status", "")

    if status in ("cancelled", "rejected"):
        return "cancelled"
    if today_str < check_in:
        return "upcoming"
    if today_str > check_out:
        return "past"
    return "active"


def _hotel_default_times(db, prop_id: int) -> dict[str, str]:
    """Resolve the hotel-wide default check-in/check-out hours from policies.

    Uses the same hotel-wide policy lookup as ``_validate_policy_times`` in
    ``reservations/service/validation.py`` (room type and season empty). The
    values are the editable policy configured by the partner; the frontend uses
    them as prefill for a new reservation instead of hardcoding 15:00/12:00.
    """
    policy = db.hotel_policies.find_one(
        {
            "prop_id": prop_id,
            "room_type_id": {"$in": ["", None]},
            "season_id": {"$in": ["", None]},
        },
        {"_id": 0, "check_in_time": 1, "check_out_time": 1},
    )
    if not policy:
        return {"check_in_time": "", "check_out_time": ""}
    return {
        "check_in_time": str(policy.get("check_in_time") or ""),
        "check_out_time": str(policy.get("check_out_time") or ""),
    }


@reception_calendar_router.get("/calendar")
def reception_calendar_api(
    prop_id: int = Query(..., ge=1),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    current_user: dict = Depends(require_permission("reservations.read")),
):
    """Return reception reservations grouped by floor, type, and physical room.

    Response shape:
    {
      "rooms": [
        {
          "room_number": "110",
          "hotel_room_id": "HR-1-110",
          "room_type_name": "Suite deluxe",
          "room_type_id": "RT-1-suite",
          "floor": "1",
          "reservations": [
            {
              "booking_id": "…",
              "guest_name": "Silvia Alarcón",
              "adults": 2,
              "children": 1,
              "check_in_date": "2026-07-15",
              "check_in_time": "15:00",
              "check_out_date": "2026-07-18",
              "check_out_time": "12:00",
              "total_nights": 3,
              "status": "confirmed",
              "visual_status": "active",   // active | upcoming | past | cancelled
              "assigned_rooms": ["HR-1-110"],
              "hotel_room_id": "HR-1-110",
              "room_number": "110",
              "total_price": 450.00,
              "currency": "USD"
            }
          ]
        }
      ],
      "start_date": "…",
      "end_date": "…",
      "today": "…"
    }

    Bookings without a physical room, legacy string assignments, or invalid
    room IDs are returned in a virtual ``UNASSIGNED`` row. That row is
    informational and must not be used as a drag-and-drop target.
    """
    db = get_database()

    today_str = local_today()

    # Default: 30 days before today → 30 days after today
    if not start_date:
        start_date = (local_now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = (local_now() + timedelta(days=30)).strftime("%Y-%m-%d")

    # Fetch ALL active physical rooms for this property (one row per door)
    hotel_rooms_docs = list(
        db.hotel_rooms.find(
            {"prop_id": prop_id, "is_active": True},
            {"_id": 0, "hotel_room_id": 1, "room_label": 1, "room_type_id": 1, "room_type_name": 1, "floor": 1},
        ).sort([("room_label", 1)])
    )

    # Resolve room type names
    rt_name_lookup: dict[str, str] = {}
    for rt in db.room_types.find({"prop_id": prop_id}, {"_id": 0, "room_type_id": 1, "name": 1}):
        rt_name_lookup[rt["room_type_id"]] = rt.get("name", "")

    # Build maps once so reservation placement stays O(bookings + assignments).
    room_by_id = {hr["hotel_room_id"]: hr for hr in hotel_rooms_docs}
    bookings_by_room: dict[str, list[dict[str, Any]]] = {hr["hotel_room_id"]: [] for hr in hotel_rooms_docs}
    unassigned_reservations: list[dict[str, Any]] = []

    # Fetch bookings that overlap the date range
    bookings = list(
        db.booking_orders.find(
            {
                "prop_id": prop_id,
                "check_in_date": {"$lte": end_date},
                "check_out_date": {"$gte": start_date},
            },
            {
                "_id": 0,
                "booking_id": 1,
                "guest_name": 1,
                "adults": 1,
                "children": 1,
                "check_in_date": 1,
                "check_in_time": 1,
                "check_out_date": 1,
                "check_out_time": 1,
                "total_nights": 1,
                "status": 1,
                "room_type_id": 1,
                "assigned_rooms": 1,
                "total_price": 1,
                "currency": 1,
            },
        )
    )

    # Place each booking into its physical rooms, or into the informational
    # virtual row when it has not been assigned yet.
    for b in bookings:
        raw_assigned = b.get("assigned_rooms") or []
        if isinstance(raw_assigned, str):
            raw_assigned = [raw_assigned]
        elif not isinstance(raw_assigned, (list, tuple)):
            raw_assigned = []

        assigned = [
            room_id
            for room_id in (
                _normalise_assigned_room_id(value)
                for value in raw_assigned
            )
            if room_id
        ]
        valid_assigned = [room_id for room_id in assigned if room_id in room_by_id]
        has_invalid_assignment = len(valid_assigned) != len(assigned)
        check_in_time_str = b.get("check_in_time") or ""
        check_out_time_str = b.get("check_out_time") or ""
        visual = _reservation_status_label(b, today_str)

        reservation_base = {
            "booking_id": b.get("booking_id", ""),
            "guest_name": b.get("guest_name", ""),
            "adults": int(b.get("adults") or 1),
            "children": int(b.get("children") or 0),
            "check_in_date": (b.get("check_in_date") or "")[:10],
            "check_in_time": check_in_time_str,
            "check_in_fraction": _parse_time_fraction(check_in_time_str),
            "check_out_date": (b.get("check_out_date") or "")[:10],
            "check_out_time": check_out_time_str,
            "check_out_fraction": _parse_time_fraction(check_out_time_str),
            "total_nights": int(b.get("total_nights") or 0),
            "status": b.get("status", ""),
            "visual_status": visual,
            "assigned_rooms": valid_assigned if not has_invalid_assignment else [],
            "total_price": b.get("total_price"),
            "currency": b.get("currency", "USD"),
        }

        if not valid_assigned or has_invalid_assignment:
            unassigned_reservations.append({
                **reservation_base,
                "hotel_room_id": "UNASSIGNED",
                "room_number": "Sin asignar",
            })
            continue

        for hrid in valid_assigned:
            hr = room_by_id[hrid]
            bookings_by_room[hrid].append({
                **reservation_base,
                "hotel_room_id": hrid,
                "room_number": hr.get("room_label") or hrid,
            })

    # Build response: one entry per physical room (even if empty). The
    # virtual row is appended only when it has data, so empty hotels keep the
    # existing compact layout.
    result_rooms = [
        {
            "room_number": hr.get("room_label") or hr["hotel_room_id"],
            "hotel_room_id": hr["hotel_room_id"],
            "room_type_name": hr.get("room_type_name") or rt_name_lookup.get(hr.get("room_type_id", ""), ""),
            "room_type_id": hr.get("room_type_id", ""),
            "floor": str(hr.get("floor") or ""),
            "reservations": sorted(
                bookings_by_room[hr["hotel_room_id"]],
                key=lambda r: (r["check_in_date"], r.get("check_in_time") or ""),
            ),
        }
        for hr in hotel_rooms_docs
    ]
    if unassigned_reservations:
        result_rooms.append({
            "room_number": "Sin asignar",
            "hotel_room_id": "UNASSIGNED",
            "room_type_name": "Reservas sin habitación",
            "room_type_id": "UNASSIGNED_TYPE",
            "floor": "",
            "reservations": sorted(
                unassigned_reservations,
                key=lambda r: (r["check_in_date"], r.get("check_in_time") or ""),
            ),
        })

    default_times = _hotel_default_times(db, prop_id)
    return {
        "rooms": result_rooms,
        "start_date": start_date,
        "end_date": end_date,
        "today": today_str,
        "check_in_time": default_times["check_in_time"],
        "check_out_time": default_times["check_out_time"],
    }
