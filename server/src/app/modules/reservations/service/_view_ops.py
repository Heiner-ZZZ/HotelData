from __future__ import annotations

from typing import Any

from pymongo import ASCENDING

from src.database.connection import get_database
from src.app.modules.partner.services import partner_hotel_policies

from ._helpers import _safe_int, _clean_text, CHECKIN_COMPLETED_STATUSES, CHECKOUT_COMPLETED_STATUSES
from .queries import hotel_booking_context
from ._hotel_options import reservation_hotel_options
from ._history_lookup import _booking_history_lookup, _guest_lookup, _derived_stay_status, _reservation_status_label


def _operational_item(
    booking: dict[str, Any],
    guest: dict[str, Any] | None,
    history: list[dict[str, Any]],
    *,
    flow: str,
) -> dict[str, Any]:
    hotel = hotel_booking_context(int(booking["prop_id"]))
    policies = partner_hotel_policies(int(booking["prop_id"])) or {}
    policy_data = policies.get("policies", {})
    stay_status = _derived_stay_status(booking, history, flow=flow)
    reference_time = (
        policy_data.get("check_in_time")
        if flow == "check_in"
        else policy_data.get("check_out_time")
    ) or "N/D"
    rooms = _safe_int(booking.get("rooms"), 1)
    room_label = f"{rooms} habitacion(es)" if rooms > 0 else "Sin asignar"
    comment = _clean_text(booking.get("comment"))
    return {
        "booking_id": booking["booking_id"],
        "prop_id": int(booking["prop_id"]),
        "hotel_label": hotel.get("hotel_label") or f"Hotel {booking['prop_id']}",
        "guest_name": (guest or {}).get("guest_name") or booking.get("guest_name") or "Huesped principal",
        "guest_email": (guest or {}).get("guest_email") or booking.get("guest_email") or "",
        "date": booking.get("check_in_date") if flow == "check_in" else booking.get("check_out_date"),
        "reservation_status": str(booking.get("status") or "requested"),
        "reservation_status_label": _reservation_status_label(str(booking.get("status") or "requested")),
        "stay_status": stay_status,
        "stay_status_label": _reservation_status_label(stay_status),
        "rooms_label": room_label,
        "estimated_time": reference_time,
        "notes": comment or "Sin notas",
        "balance_label": "N/D",
        "can_complete": stay_status not in (CHECKIN_COMPLETED_STATUSES if flow == "check_in" else CHECKOUT_COMPLETED_STATUSES)
        and booking.get("status") not in {"cancelled", "rejected"},
        "history_count": len(history),
    }


def _list_operational_bookings(*, flow: str, operation_date: str, prop_id: int | None = None) -> dict[str, Any]:
    db = get_database()
    field = "check_in_date" if flow == "check_in" else "check_out_date"
    filters: dict[str, Any] = {field: operation_date}
    if prop_id:
        filters["prop_id"] = prop_id
    items = list(
        db.booking_orders.find(filters, {"_id": 0}).sort([(field, ASCENDING), ("created_at", ASCENDING)])
    )
    booking_ids = [item["booking_id"] for item in items]
    guest_lookup = _guest_lookup(booking_ids)
    history_lookup = _booking_history_lookup(booking_ids)
    view_items = [
        _operational_item(item, guest_lookup.get(item["booking_id"]), history_lookup.get(item["booking_id"], []), flow=flow)
        for item in items
    ]
    total = len(view_items)
    completed_key = "checked_in" if flow == "check_in" else "checked_out"
    summary = {
        "arrivals_today" if flow == "check_in" else "departures_today": total,
        "pending": sum(1 for item in view_items if item["stay_status"] == "pending"),
        "completed": sum(1 for item in view_items if item["stay_status"] == completed_key),
        "cancelled_or_no_show": sum(1 for item in view_items if item["stay_status"] in {"cancelled", "no_show"}),
    }
    return {
        "operation_date": operation_date,
        "prop_id": prop_id,
        "property_options": reservation_hotel_options(limit=100),
        "summary": summary,
        "items": view_items,
    }


def list_check_ins(*, operation_date: str, prop_id: int | None = None) -> dict[str, Any]:
    return _list_operational_bookings(flow="check_in", operation_date=operation_date, prop_id=prop_id)


def list_check_outs(*, operation_date: str, prop_id: int | None = None) -> dict[str, Any]:
    return _list_operational_bookings(flow="check_out", operation_date=operation_date, prop_id=prop_id)
