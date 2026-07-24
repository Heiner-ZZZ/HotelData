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


@reception_calendar_router.get("/calendar")
def reception_calendar_api(
    prop_id: int = Query(..., ge=1),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    current_user: dict = Depends(require_permission("reservations.read")),
):
    """Return reservations for a property grouped by room type for the reception calendar.

    Response shape:
    {
      "room_types": [
        {
          "room_type_id": "…",
          "room_type_name": "Suite deluxe",
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
              "assigned_rooms": ["Suite 1"],
              "room_number": "Suite 1",
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
            {"_id": 0, "hotel_room_id": 1, "room_label": 1, "room_type_id": 1, "room_type_name": 1},
        ).sort([("room_label", 1)])
    )

    # Resolve room type names
    rt_name_lookup: dict[str, str] = {}
    for rt in db.room_types.find({"prop_id": prop_id}, {"_id": 0, "room_type_id": 1, "name": 1}):
        rt_name_lookup[rt["room_type_id"]] = rt.get("name", "")

    # Build map: hotel_room_id → list of reservations assigned to that room
    bookings_by_room: dict[str, list[dict[str, Any]]] = {hr["hotel_room_id"]: [] for hr in hotel_rooms_docs}

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

    # Place each booking into the rooms it is assigned to
    for b in bookings:
        assigned = b.get("assigned_rooms") or []
        if not assigned:
            continue  # unassigned bookings don't appear on the calendar

        check_in_time_str = b.get("check_in_time") or ""
        check_out_time_str = b.get("check_out_time") or ""
        visual = _reservation_status_label(b, today_str)

        for hrid in assigned:
            if hrid not in bookings_by_room:
                continue
            hr = next((hr for hr in hotel_rooms_docs if hr["hotel_room_id"] == hrid), None)
            room_num = hr.get("room_label") or hrid if hr else hrid

            bookings_by_room[hrid].append({
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
                "assigned_rooms": assigned,
                "hotel_room_id": hrid,
                "room_number": room_num,
                "total_price": b.get("total_price"),
                "currency": b.get("currency", "USD"),
            })

    # Build response: one entry per physical room (even if empty)
    result_rooms = [
        {
            "room_number": hr.get("room_label") or hr["hotel_room_id"],
            "hotel_room_id": hr["hotel_room_id"],
            "room_type_name": hr.get("room_type_name") or rt_name_lookup.get(hr.get("room_type_id", ""), ""),
            "room_type_id": hr.get("room_type_id", ""),
            "reservations": sorted(
                bookings_by_room[hr["hotel_room_id"]],
                key=lambda r: (r["check_in_date"], r.get("check_in_time") or ""),
            ),
        }
        for hr in hotel_rooms_docs
    ]

    return {
        "rooms": result_rooms,
        "start_date": start_date,
        "end_date": end_date,
        "today": today_str,
    }
