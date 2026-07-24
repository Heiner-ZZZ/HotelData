"""Simplified check-in detail service.

Stores only the essential fields a receptionist needs to enter:
  - check_in_arrival_time         (str)   — hora real de llegada
  - check_in_has_companions       (bool)  — si llegó acompañado
  - check_in_companions_count     (int)   — cuántos acompañantes
  - check_in_document_verified    (bool)  — documento verificado
  - check_in_keys_delivered       (bool)  — llaves entregadas
  - check_in_payment_pending      (bool)  — pago pendiente (informativo)
  - check_in_deposit_received     (bool)  — depósito recibido
  - check_in_privacy_signed       (bool)  — políticas aceptadas
  - check_in_observations         (str)   — observaciones

Saved directly on the booking_orders document.
"""

from __future__ import annotations

import logging
from typing import Any

from src.database.connection import get_database
from ._helpers import utc_now
from .queries import hotel_booking_context

logger = logging.getLogger(__name__)


def get_check_in_detail(booking_id: str) -> dict[str, Any]:
    """Return booking info + check-in fields for the check-in page."""
    db = get_database()

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {
            "_id": 0, "booking_id": 1, "prop_id": 1, "guest_name": 1,
            "guest_email": 1, "guest_phone": 1, "cedula": 1,
            "check_in_date": 1, "check_in_date_actual": 1, "check_in_time_actual": 1,
            "check_out_date": 1, "total_price": 1, "currency": 1,
            "total_nights": 1, "rooms": 1, "adults": 1, "children": 1,
            "status": 1, "stay_status": 1, "room_type_id": 1,
            "assigned_rooms": 1, "folio": 1, "check_in_by": 1,
            "payment_method": 1, "booking_source": 1, "comment": 1,
            "check_in_arrival_time": 1, "check_in_has_companions": 1,
            "check_in_companions_count": 1, "check_in_document_verified": 1,
            "check_in_keys_delivered": 1,
            "check_in_payment_pending": 1, "check_in_deposit_received": 1,
            "check_in_privacy_signed": 1, "check_in_observations": 1,
        },
    )
    if not booking:
        raise ValueError("Booking not found")

    # Room type name
    room_type_name = ""
    room_type_id = booking.get("room_type_id", "") or ""
    if room_type_id:
        rt = db.room_types.find_one(
            {"room_type_id": room_type_id, "prop_id": int(booking.get("prop_id", 0))},
            {"_id": 0, "name": 1},
        )
        room_type_name = rt.get("name", room_type_id) if rt else room_type_id

    hotel_label = hotel_booking_context(int(booking.get("prop_id", 0))).get("hotel_label", "") or f"Hotel {booking.get('prop_id', '')}"

    # Resolve assigned rooms
    assigned_rooms: list[dict[str, Any]] = []
    raw_ids = booking.get("assigned_rooms") or []
    if raw_ids:
        room_docs = list(
            db.hotel_rooms.find(
                {"hotel_room_id": {"$in": raw_ids}},
                {"_id": 0, "hotel_room_id": 1, "room_label": 1, "floor": 1},
            )
        )
        labels = [r.get("room_label", "") for r in room_docs if r.get("room_label")]
        status_map = {}
        if labels:
            for doc in db.room_status_log.find(
                {"prop_id": int(booking.get("prop_id", 0)), "room_label": {"$in": labels}},
                {"_id": 0, "room_label": 1, "status": 1},
            ):
                status_map[doc["room_label"]] = doc["status"]
        for r in room_docs:
            label = r.get("room_label", "")
            assigned_rooms.append({
                "hotel_room_id": r["hotel_room_id"],
                "room_number": r.get("room_label", ""),
                "room_label": r.get("room_label", ""),
                "floor": r.get("floor", ""),
                "room_status": status_map.get(label, "unknown"),
            })

    return {
        "booking_id": booking_id,
        "prop_id": int(booking.get("prop_id", 0)),
        "hotel_label": hotel_label,
        "guest_name": booking.get("guest_name", ""),
        "guest_email": booking.get("guest_email", ""),
        "guest_phone": booking.get("guest_phone", ""),
        "cedula": booking.get("cedula", ""),
        "check_in_date": booking.get("check_in_date", ""),
        "check_in_date_actual": booking.get("check_in_date_actual"),
        "check_in_time_actual": booking.get("check_in_time_actual"),
        "check_out_date": booking.get("check_out_date", ""),
        "total_price": booking.get("total_price"),
        "currency": booking.get("currency", "USD"),
        "total_nights": booking.get("total_nights", 0),
        "rooms": booking.get("rooms", 1),
        "adults": booking.get("adults", 1),
        "children": booking.get("children", 0),
        "status": booking.get("status", ""),
        "stay_status": booking.get("stay_status", ""),
        "room_type_id": room_type_id,
        "room_type_name": room_type_name,
        "folio": booking.get("folio"),
        "check_in_by": booking.get("check_in_by"),
        "payment_method": booking.get("payment_method", ""),
        "booking_source": booking.get("booking_source", ""),
        "comment": booking.get("comment", ""),
        "assigned_rooms": assigned_rooms,
        # Check-in fields
        "check_in_arrival_time": booking.get("check_in_arrival_time", ""),
        "check_in_has_companions": booking.get("check_in_has_companions", False),
        "check_in_companions_count": booking.get("check_in_companions_count", 0),
        "check_in_document_verified": booking.get("check_in_document_verified", False),
        "check_in_keys_delivered": booking.get("check_in_keys_delivered", False),
        "check_in_payment_pending": booking.get("check_in_payment_pending", False),
        "check_in_deposit_received": booking.get("check_in_deposit_received", False),
        "check_in_privacy_signed": booking.get("check_in_privacy_signed", False),
        "check_in_observations": booking.get("check_in_observations", ""),
    }


def save_check_in_detail(
    booking_id: str,
    *,
    check_in_arrival_time: str | None = None,
    check_in_has_companions: bool | None = None,
    check_in_companions_count: int | None = None,
    check_in_document_verified: bool | None = None,
    check_in_keys_delivered: bool | None = None,
    check_in_payment_pending: bool | None = None,
    check_in_deposit_received: bool | None = None,
    check_in_privacy_signed: bool | None = None,
    check_in_observations: str | None = None,
    changed_by: str = "web",
) -> dict[str, Any]:
    """Save check-in detail fields on booking_orders as a draft."""
    db = get_database()

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "status": 1, "is_test": 1},
    )
    if not booking:
        raise ValueError("Booking not found")
    if booking.get("status") in ("cancelled", "rejected"):
        raise ValueError("Cannot modify check-in detail for a cancelled or rejected booking")

    set_fields: dict[str, Any] = {}
    for key, val in [
        ("check_in_arrival_time", check_in_arrival_time),
        ("check_in_has_companions", check_in_has_companions),
        ("check_in_companions_count", check_in_companions_count),
        ("check_in_document_verified", check_in_document_verified),
        ("check_in_keys_delivered", check_in_keys_delivered),
        ("check_in_payment_pending", check_in_payment_pending),
        ("check_in_deposit_received", check_in_deposit_received),
        ("check_in_privacy_signed", check_in_privacy_signed),
        ("check_in_observations", check_in_observations),
    ]:
        if val is not None:
            set_fields[key] = val

    if not set_fields:
        return {"booking_id": booking_id, "updated": False}

    set_fields["updated_at"] = utc_now()
    db.booking_orders.update_one({"booking_id": booking_id}, {"$set": set_fields})

    data_fields = list(set_fields.keys())
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": booking.get("status", "unknown"),
        "changed_at": utc_now(),
        "reason": f"check_in_detail_updated: {', '.join(data_fields)}",
        "changed_by": changed_by,
        "is_test": bool(booking.get("is_test", False)),
    })

    return {"booking_id": booking_id, "updated": True, "fields_updated": data_fields}
