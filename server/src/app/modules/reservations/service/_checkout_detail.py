"""Check-out detail service.

Fetches all data needed for the Liquidation & Check-Out page:
  - Booking info (guest, room, dates, folio)
  - Invoice data (line items, subtotals, taxes, total)
  - Additional charges (consumptions)
  - Payment / deposit info

Also provides a save function to store checkout-specific fields
before finalizing the check-out.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from src.database.connection import get_database

from ._checkinout._checkout import get_late_checkout_context
from ._helpers import utc_now
from .queries import hotel_booking_context

logger = logging.getLogger(__name__)


def get_check_out_detail(booking_id: str) -> dict[str, Any]:
    """Return full check-out detail: booking info + invoice + charges."""
    db = get_database()

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {
            "_id": 0, "booking_id": 1, "prop_id": 1, "guest_name": 1,
            "guest_email": 1, "guest_phone": 1, "cedula": 1,
            "check_in_date": 1, "check_out_date": 1,
            "check_in_date_actual": 1, "check_in_time_actual": 1,
            "total_price": 1, "currency": 1, "total_nights": 1,
            "rooms": 1, "room_type_id": 1,
            "assigned_rooms": 1, "folio": 1, "no_show_penalty_amount": 1,
            "no_show_penalty_percent": 1, "check_in_by": 1, "shift_id": 1,
            "payment_method": 1, "booking_source": 1, "status": 1, "stay_status": 1,
            "total_charges": 1,
            "check_out_date_actual": 1, "check_out_time_actual": 1, "check_out_by": 1,
            "check_out_room_inspected": 1, "check_out_keys_returned": 1,
            "check_out_damages_found": 1, "check_out_late_checkout_fee": 1,
            "check_out_mode": 1, "late_checkout_fee": 1, "late_checkout_minutes": 1,
            "late_checkout_approved_by": 1, "late_checkout_reason": 1,
            "late_checkout_policy_time": 1,
            "check_out_payment_method": 1, "check_out_payment_ref": 1,
            "check_out_observations": 1,
        },
    )
    if not booking:
        raise ValueError("No se encontró la reserva. Verificá el número de reserva e intentá de nuevo.")

    prop_id = int(booking.get("prop_id", 0))
    hotel_label = hotel_booking_context(prop_id).get("hotel_label", "") or f"Hotel {prop_id}"

    # Late check-out window (server-authoritative): the front desk needs the
    # governed context (courtesy vs approval, fee default, policy hour) before
    # completing a same-day departure past the check-out hour.
    late_checkout_context = get_late_checkout_context(
        prop_id,
        str(booking.get("check_out_date", "") or ""),
        db=db,
    )

    # ``booking_orders.folio`` is a denormalized display field. Historical
    # rows and migrated no-shows may have the authoritative number only in
    # ``guest_folios``; read it here so a fresh checkout page can rebuild its
    # billing link without depending on transient UI state.
    folio_doc = db.guest_folios.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "folio_number": 1},
    )

    # Room type name
    room_type_name = ""
    room_type_id = booking.get("room_type_id", "") or ""
    if room_type_id:
        rt = db.room_types.find_one(
            {"room_type_id": room_type_id, "prop_id": prop_id},
            {"_id": 0, "name": 1},
        )
        room_type_name = rt.get("name", room_type_id) if rt else room_type_id

    # Assigned rooms
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
        status_map: dict[str, str] = {}
        if labels:
            for doc in db.room_status_log.find(
                {"prop_id": prop_id, "room_label": {"$in": labels}},
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

    # Invoice
    invoice: dict[str, Any] | None = None
    inv = db.reservation_invoices.find_one(
        {"booking_id": booking_id},
        {"_id": 1, "invoice_number": 1, "subtotal": 1, "room_subtotal": 1,
         "extras_total": 1, "taxes": 1, "total": 1, "status": 1,
         "issued_at": 1, "paid_at": 1, "line_items": 1, "notes": 1},
    )
    if inv:
        # Lo que la facturación ya cubre: suma de subtotales de TODAS las
        # facturas no canceladas del booking (principal + complementarias).
        # La nota de reconciliación compara el subtotal vivo contra este total,
        # así una factura complementaria del gap la despeja al recargar.
        covered_subtotal = round(sum(
            float(i.get("subtotal", 0) or 0)
            for i in db.reservation_invoices.find(
                {"booking_id": booking_id, "status": {"$ne": "cancelled"}},
                {"subtotal": 1},
            )
        ), 2)
        invoice = {
            "id": str(inv["_id"]),
            "invoice_number": inv.get("invoice_number", ""),
            "subtotal": inv.get("subtotal", 0),
            "covered_subtotal": covered_subtotal,
            "room_subtotal": inv.get("room_subtotal", 0),
            "extras_total": inv.get("extras_total", 0),
            "taxes": inv.get("taxes", 0),
            "total": inv.get("total", 0),
            "status": inv.get("status", ""),
            "issued_at": inv.get("issued_at").isoformat() if isinstance(inv.get("issued_at"), datetime) else str(inv.get("issued_at", "")),
            "paid_at": inv.get("paid_at").isoformat() if isinstance(inv.get("paid_at"), datetime) else str(inv.get("paid_at", "")) if inv.get("paid_at") else None,
            "notes": inv.get("notes"),
            "line_items": inv.get("line_items", []),
        }

    # Additional charges
    from src.app.modules.housekeeping.service.collections import CHARGES_COLLECTION
    charges = list(
        db[CHARGES_COLLECTION].find(
            {"booking_id": booking_id},
            {"_id": 0, "concept": 1, "amount": 1, "quantity": 1, "total": 1, "category": 1, "note": 1, "created_at": 1},
        ).sort("created_at", -1)
    )
    charges_total = round(sum(float(c.get("total", 0) or 0) for c in charges), 2)

    # Group charges by category
    charges_by_category: dict[str, list[dict[str, Any]]] = {}
    category_totals: dict[str, float] = {}
    for c in charges:
        cat = c.get("category", "otros") or "otros"
        charges_by_category.setdefault(cat, []).append(c)
        category_totals[cat] = round(category_totals.get(cat, 0) + float(c.get("total", 0) or 0), 2)

    # Payment / deposit info
    deposit = booking.get("check_in_deposit_received", False)
    payment_pending = booking.get("check_in_payment_pending", True)

    # Shift attribution: the front-desk cash shift that handled the check-out
    # (stamped at completion). Resolves the responsible cashier + shift label
    # so the liquidation page can show who processed the money movement.
    check_out_shift_id: str | None = None
    check_out_shift: dict[str, Any] | None = None
    raw_shift_id = booking.get("shift_id")
    if raw_shift_id:
        from src.app.modules.reception import get_shift
        from src.app.modules.reception.shifts import get_shift_labels
        check_out_shift_id = str(raw_shift_id)
        shift_doc = get_shift(check_out_shift_id)
        if shift_doc:
            shift_type = shift_doc.get("shift_type") or ""
            check_out_shift = {
                "shift_type": shift_type,
                "shift_label": get_shift_labels(prop_id).get(shift_type, shift_type) or None,
                "employee": shift_doc.get("employee"),
                "opened_by": shift_doc.get("opened_by"),
                "start_time": shift_doc.get("start_time"),
            }

    # Check-out fields
    check_out_fields = {
        "check_out_room_inspected": booking.get("check_out_room_inspected", False),
        "check_out_keys_returned": booking.get("check_out_keys_returned", False),
        "check_out_damages_found": booking.get("check_out_damages_found", False),
        "check_out_late_checkout_fee": booking.get("check_out_late_checkout_fee", 0),
        "check_out_mode": booking.get("check_out_mode"),
        "late_checkout_fee": booking.get("late_checkout_fee", 0),
        "late_checkout_minutes": booking.get("late_checkout_minutes", 0),
        "late_checkout_approved_by": booking.get("late_checkout_approved_by"),
        "late_checkout_reason": booking.get("late_checkout_reason", ""),
        # Hora de política estampada al completar (fuente de verdad del detalle,
        # vs el contexto en vivo que se resuelve al abrir la página).
        "late_checkout_policy_time": booking.get("late_checkout_policy_time", ""),
        "check_out_discount": booking.get("check_out_discount", 0),
        "check_out_discount_reason": booking.get("check_out_discount_reason", ""),
        "check_out_payment_method": booking.get("check_out_payment_method", ""),
        "check_out_payment_ref": booking.get("check_out_payment_ref", ""),
        "check_out_observations": booking.get("check_out_observations", ""),
        "check_out_date_actual": booking.get("check_out_date_actual"),
        "check_out_time_actual": booking.get("check_out_time_actual"),
        "check_out_by": booking.get("check_out_by"),
        "check_out_shift_id": check_out_shift_id,
        "check_out_shift": check_out_shift,
    }

    return {
        "booking_id": booking_id,
        "prop_id": prop_id,
        "hotel_label": hotel_label,
        "folio": booking.get("folio") or (folio_doc or {}).get("folio_number"),
        "no_show_penalty_amount": booking.get("no_show_penalty_amount"),
        "no_show_penalty_percent": booking.get("no_show_penalty_percent"),
        "guest_name": booking.get("guest_name", ""),
        "guest_email": booking.get("guest_email", ""),
        "guest_phone": booking.get("guest_phone", ""),
        "cedula": booking.get("cedula", ""),
        "check_in_date": booking.get("check_in_date", ""),
        "check_in_date_actual": booking.get("check_in_date_actual"),
        "check_in_time_actual": booking.get("check_in_time_actual"),
        "check_in_by": booking.get("check_in_by"),
        "check_out_date": booking.get("check_out_date", ""),
        "total_price": booking.get("total_price"),
        "currency": booking.get("currency", "USD"),
        "total_nights": booking.get("total_nights", 0),
        "rooms": booking.get("rooms", 1),
        "room_type_name": room_type_name,
        "assigned_rooms": assigned_rooms,
        "status": booking.get("status", ""),
        "stay_status": booking.get("stay_status", ""),
        "payment_method": booking.get("payment_method", ""),
        "booking_source": booking.get("booking_source", ""),
        "total_charges": charges_total,
        "deposit_received": deposit,
        "payment_pending": payment_pending,
        # Invoice
        "invoice": invoice,
        # Charges
        "charges": charges,
        "charges_total": charges_total,
        "charges_by_category": charges_by_category,
        "category_totals": category_totals,
        # Late check-out window (governed by hotel policy)
        "late_checkout_context": late_checkout_context,
        # Check-out fields
        **check_out_fields,
    }


def save_check_out_detail(
    booking_id: str,
    *,
    check_out_room_inspected: bool | None = None,
    check_out_keys_returned: bool | None = None,
    check_out_damages_found: bool | None = None,
    check_out_late_checkout_fee: float | None = None,
    check_out_discount: float | None = None,
    check_out_discount_reason: str | None = None,
    check_out_payment_method: str | None = None,
    check_out_payment_ref: str | None = None,
    check_out_observations: str | None = None,
    changed_by: str = "web",
) -> dict[str, Any]:
    """Save check-out detail fields on booking_orders as a draft."""
    db = get_database()

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "status": 1, "is_test": 1},
    )
    if not booking:
        raise ValueError("No se encontró la reserva. Verificá el número de reserva e intentá de nuevo.")
    if booking.get("status") in ("cancelled", "rejected"):
        raise ValueError(
            "No se puede modificar el detalle de check-out de una reserva cancelada o rechazada. "
            "Creá una reserva nueva o contactá al equipo."
        )

    set_fields: dict[str, Any] = {}
    for key, val in [
        ("check_out_room_inspected", check_out_room_inspected),
        ("check_out_keys_returned", check_out_keys_returned),
        ("check_out_damages_found", check_out_damages_found),
        ("check_out_late_checkout_fee", check_out_late_checkout_fee),
        ("check_out_discount", check_out_discount),
        ("check_out_discount_reason", check_out_discount_reason),
        ("check_out_payment_method", check_out_payment_method),
        ("check_out_payment_ref", check_out_payment_ref),
        ("check_out_observations", check_out_observations),
    ]:
        if val is not None:
            set_fields[key] = val

    if not set_fields:
        return {"booking_id": booking_id, "updated": False, "fields_updated": []}

    set_fields["updated_at"] = utc_now()
    db.booking_orders.update_one({"booking_id": booking_id}, {"$set": set_fields})

    data_fields = list(set_fields.keys())
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": booking.get("status", "unknown"),
        "changed_at": utc_now(),
        "reason": f"check_out_detail_updated: {', '.join(data_fields)}",
        "changed_by": changed_by,
        "is_test": bool(booking.get("is_test", False)),
    })

    return {"booking_id": booking_id, "updated": True, "fields_updated": data_fields}
