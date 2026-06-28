"""Reception calendar — visual occupancy bars for the recepción page."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query

from src.app.security.dependencies import require_login
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
    current_user: dict = Depends(require_login),
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

    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    # Default: 30 days before today → 30 days after today
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

    # Fetch room types for this property
    room_types_docs = list(
        db.room_types.find(
            {"prop_id": prop_id},
            {"_id": 0, "room_type_id": 1, "name": 1},
        ).sort([("name", 1)])
    )

    rt_map = {rt["room_type_id"]: rt["name"] for rt in room_types_docs}

    # Build a lookup map: hotel_room_id → {room_number, room_label}
    # assigned_rooms in booking_orders stores hotel_room_id values
    hotel_rooms_docs = list(
        db.hotel_rooms.find(
            {"prop_id": prop_id, "is_active": True},
            {"_id": 0, "hotel_room_id": 1, "room_number": 1, "room_label": 1},
        )
    )
    room_id_map: dict[str, dict[str, str]] = {}
    for hr in hotel_rooms_docs:
        room_id_map[hr["hotel_room_id"]] = {
            "room_number": hr.get("room_number", ""),
            "room_label": hr.get("room_label", ""),
        }

    # Fetch all bookings that overlap the date range
    # A booking overlaps if check_in_date <= end_date AND check_out_date >= start_date
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

    # Group by room_type_id
    grouped: dict[str, list[dict[str, Any]]] = {}
    for b in bookings:
        rt_id = b.get("room_type_id") or "unknown"
        if rt_id not in grouped:
            grouped[rt_id] = []

        visual = _reservation_status_label(b, today_str)
        assigned = b.get("assigned_rooms") or []
        # assigned_rooms contains hotel_room_id values — resolve display names
        hotel_room_id = assigned[0] if assigned else ""
        resolved = room_id_map.get(hotel_room_id, {}) if hotel_room_id else {}
        room_number = resolved.get("room_number") or resolved.get("room_label") or hotel_room_id

        check_in_time_str = b.get("check_in_time") or ""
        check_out_time_str = b.get("check_out_time") or ""

        grouped[rt_id].append({
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
            "room_number": room_number,
            "hotel_room_id": hotel_room_id,
            "total_price": b.get("total_price"),
            "currency": b.get("currency", "USD"),
        })

    # Build final response
    result_room_types = []
    for rt in room_types_docs:
        rt_id = rt["room_type_id"]
        reservations = grouped.get(rt_id, [])
        # Sort by check_in_date then check_in_time
        reservations.sort(key=lambda r: (r["check_in_date"], r.get("check_in_time") or ""))
        result_room_types.append({
            "room_type_id": rt_id,
            "room_type_name": rt["name"],
            "reservations": reservations,
        })

    return {
        "room_types": result_room_types,
        "start_date": start_date,
        "end_date": end_date,
        "today": today_str,
    }
