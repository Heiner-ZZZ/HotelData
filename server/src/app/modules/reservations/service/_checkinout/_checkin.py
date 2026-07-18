"""Check-in operations."""

from __future__ import annotations

import logging
import threading
from datetime import date
from typing import Any

from src.database.connection import get_database
from .._helpers import utc_now
from src.app.core.timezone import local_today
from src.app.modules.reservations.service._checkinout._helpers import (
    _generate_folio,
    _notify_guest_check_in,
    _notify_staff_check_in,
)
from src.app.core.state_machine import CHECKIN_ALLOWED_ROOM_STATUSES, CHECKIN_REJECTED_ROOM_STATUSES
from src.app.modules.partner.services.audit import register_action

logger = logging.getLogger(__name__)


def update_check_in_datetime(
    booking_id: str,
    *,
    check_in_date: str | None = None,
    check_in_time: str | None = None,
    changed_by: str = "web",
) -> dict[str, Any]:
    """Update check-in date and/or time for an active booking."""
    db = get_database()
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "status": 1, "stay_status": 1, "is_test": 1},
    )
    if not booking:
        raise ValueError("Booking not found")
    if booking.get("status") in ("cancelled", "rejected"):
        raise ValueError("Cannot modify a cancelled or rejected booking")

    now = utc_now()
    update_fields: dict[str, Any] = {"updated_at": now}
    reason_parts = []
    if check_in_date is not None:
        update_fields["check_in_date"] = check_in_date
        reason_parts.append(f"fecha: {check_in_date}")
    if check_in_time is not None:
        update_fields["check_in_time"] = check_in_time
        reason_parts.append(f"hora: {check_in_time}")

    if len(update_fields) == 1:
        return {"booking_id": booking_id, "updated": False, "detail": "No changes provided"}

    db.booking_orders.update_one({"booking_id": booking_id}, {"$set": update_fields})
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": booking.get("status", "unknown"),
        "changed_at": now,
        "reason": f"check-in actualizado: {', '.join(reason_parts)}",
        "changed_by": changed_by,
        "is_test": bool(booking.get("is_test", False)),
    })
    return {"booking_id": booking_id, "updated": True}


def complete_check_in(
    booking_id: str,
    *,
    changed_by: str = "web",
    payment_method: str = "",
    ip_address: str = "",
    observations: str = "",
) -> dict[str, Any]:
    db = get_database()

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "guest_name": 1, "guest_email": 1, "prop_id": 1, "is_test": 1,
         "check_in_date": 1, "check_out_date": 1, "total_price": 1, "currency": 1, "total_nights": 1,
         "assigned_rooms": 1},
    )
    if not booking:
        raise ValueError("booking not found")

    # ── Validate check-in date is not in the past ──
    check_in_date_str = booking.get("check_in_date", "")
    if check_in_date_str:
        try:
            ci_date = date.fromisoformat(check_in_date_str)
            today = date.fromisoformat(local_today())
            if ci_date < today:
                raise ValueError(
                    f"No se puede realizar check-in para una fecha pasada. "
                    f"La fecha de check-in ({check_in_date_str}) es anterior a hoy ({today.isoformat()})."
                )
        except ValueError as exc:
            if str(exc).startswith("No se puede"):
                raise
            logger.warning("Could not parse check_in_date '%s' for booking %s", check_in_date_str, booking_id)

    # ── Validate room status before check-in ──
    assigned_rooms: list[str] = booking.get("assigned_rooms") or []
    _room_docs: list[dict[str, Any]] = []

    if assigned_rooms:
        _room_docs = list(
            db.hotel_rooms.find(
                {"hotel_room_id": {"$in": assigned_rooms}},
                {"_id": 0, "hotel_room_id": 1, "room_label": 1, "room_number": 1},
            )
        )
        room_labels = {r["hotel_room_id"]: r.get("room_label", "") or r.get("room_number", "") for r in _room_docs}
        status_query_labels = [v for v in room_labels.values() if v]
        if status_query_labels:
            status_docs = list(
                db.room_status_log.find(
                    {"prop_id": booking["prop_id"], "room_label": {"$in": status_query_labels}},
                    {"_id": 0, "room_label": 1, "status": 1},
                )
            )
            room_status_map: dict[str, str] = {r["room_label"]: r["status"] for r in status_docs}
            blocked: list[str] = []
            for h_id in assigned_rooms:
                label = room_labels.get(h_id, "")
                if not label:
                    continue
                status = room_status_map.get(label, "unknown")
                if status not in CHECKIN_ALLOWED_ROOM_STATUSES:
                    blocked.append(f"{label} ({status})")
            if blocked:
                raise ValueError(
                    f"No se puede realizar el check-in. Las siguientes habitaciones no están disponibles: "
                    f"{', '.join(blocked)}. Solo se permite check-in en habitaciones en estado 'vacante_limpia' o 'vacante_sucia'. "
                    f"Estados rechazados: {', '.join(sorted(CHECKIN_REJECTED_ROOM_STATUSES))}."
                )

    changed_at = utc_now()
    folio = _generate_folio(int(booking.get("prop_id", 0)))

    result = db.booking_orders.find_one_and_update(
        {"booking_id": booking_id, "status": {"$nin": ["cancelled", "rejected"]}, "stay_status": {"$ne": "checked_in"}},
        {
            "$set": {
                "stay_status": "checked_in",
                "updated_at": changed_at,
                "folio": folio,
                "check_in_date_actual": changed_at.strftime("%Y-%m-%d"),
                "check_in_time_actual": changed_at.strftime("%H:%M"),
                "check_in_by": changed_by,
                "payment_method": payment_method or booking.get("payment_method", ""),
            }
        },
        projection={"_id": 0, "is_test": 1},
    )
    if result is None:
        existing = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0, "status": 1, "stay_status": 1})
        if existing is None:
            raise ValueError("booking not found")
        if existing.get("stay_status") == "checked_in":
            raise ValueError("booking already checked in")
        raise ValueError("booking cannot be checked in from current reservation status")

    audit_entry: dict[str, Any] = {
        "booking_id": booking_id, "status": "checked_in",
        "changed_at": changed_at, "reason": "front_desk_check_in",
        "changed_by": changed_by, "is_test": bool(result.get("is_test")),
        "check_in_method": "manual",
    }
    if ip_address:
        audit_entry["ip_address"] = ip_address
    if observations:
        audit_entry["observations"] = observations
    db.booking_status_history.insert_one(audit_entry)

    # ── Audit log (universal) ──
    if booking and not booking.get("is_test"):
        try:
            register_action(
                prop_id=int(booking.get("prop_id", 0)),
                entity_type="reservation",
                entity_id=booking_id,
                action="check_in",
                summary=f"Check-in completado — {booking.get('guest_name', '')} — Folio {folio}",
                changed_by=changed_by,
                metadata={"folio": folio, "guest_name": booking.get("guest_name", ""),
                         "payment_method": payment_method or booking.get("payment_method", ""),
                         "observations": observations},
            )
        except Exception:
            logger.exception("Failed to register audit action for check-in %s", booking_id)

    # ── Notifications ──
    if booking:
        guest_email = (booking.get("guest_email") or "").strip()
        if guest_email and not booking.get("is_test"):
            threading.Thread(target=_notify_guest_check_in, args=(booking_id, booking), daemon=True).start()
    if booking and not booking.get("is_test"):
        threading.Thread(target=_notify_staff_check_in, args=(booking_id, booking), daemon=True).start()

    # ── Register shift transaction ──
    if booking and not booking.get("is_test"):
        try:
            from src.app.modules.reception import register_transaction
            register_transaction(
                prop_id=int(booking.get("prop_id", 0)),
                txn_type="check_in", booking_id=booking_id,
                description=f"Check-in: {booking.get('guest_name', '')} — Folio {folio}",
            )
        except Exception:
            logger.exception("Failed to register shift transaction for check-in %s", booking_id)

    # ── Auto-create or retrieve invoice ──
    invoice_id: str | None = None
    if result and not result.get("is_test"):
        existing_inv = db.reservation_invoices.find_one({"booking_id": booking_id})
        if existing_inv:
            invoice_id = str(existing_inv["_id"])
        else:
            total = booking.get("total_price") if booking else None
            if total is not None and float(total) > 0:
                try:
                    from src.app.modules.billing.schemas import InvoiceCreate
                    from src.app.modules.billing.service import create_invoice
                    subtotal = float(total)
                    taxes = round(subtotal * 0.10, 2)
                    inv = create_invoice(InvoiceCreate(
                        booking_id=booking_id, subtotal=subtotal, taxes=taxes,
                        notes=f"Auto-generated invoice for booking {booking_id} at check-in",
                    ))
                    if inv:
                        invoice_id = inv.get("id")
                except Exception:
                    logger.exception("Failed to auto-create invoice at check-in for booking %s", booking_id)

    # ── Mark rooms as occupied ──
    if assigned_rooms and booking:
        try:
            for r in _room_docs:
                label = r.get("room_label", "") or r.get("room_number", "")
                if label:
                    db.room_status_log.update_one(
                        {"prop_id": booking["prop_id"], "room_label": label},
                        {"$set": {"status": "occupied_clean", "note": f"Check-in: {booking_id}", "updated_at": changed_at},
                         "$setOnInsert": {"created_at": changed_at}},
                        upsert=True,
                    )
            logger.info("Rooms marked as occupied for booking %s", booking_id)
        except Exception:
            logger.exception("Failed to mark rooms as occupied for booking %s", booking_id)

    # ── Notify housekeeping ──
    if assigned_rooms and booking and not booking.get("is_test"):
        try:
            room_labels_str = ", ".join(
                r.get("room_label", "") or r.get("room_number", "") for r in _room_docs
            ) or str(len(assigned_rooms))
            db.notification_log.insert_one({
                "notification_type": "housekeeping_check_in",
                "entity_type": "booking", "entity_id": booking_id,
                "prop_id": booking["prop_id"], "recipient_email": "",
                "subject": f"Check-in: habitación(es) {room_labels_str} ocupadas",
                "message": (
                    f"El huésped {booking.get('guest_name', '')} ha realizado el check-in. "
                    f"Habitación(es): {room_labels_str}. "
                    f"Check-out: {booking.get('check_out_date', '')}."
                ),
                "status": "pending", "created_at": changed_at,
                "metadata": {"booking_id": booking_id, "assigned_rooms": assigned_rooms,
                             "guest_name": booking.get("guest_name", ""),
                             "check_out_date": booking.get("check_out_date", "")},
            })
        except Exception:
            logger.exception("Failed to notify housekeeping for booking %s", booking_id)

    # ── Create folio ──
    folio_id: str | None = None
    if booking and not booking.get("is_test"):
        try:
            from src.app.modules.billing.service import create_folio
            folio_doc = create_folio(booking_id)
            if folio_doc:
                folio_id = folio_doc.get("folio_number")
                logger.info("Folio %s created for booking %s at check-in", folio_id, booking_id)
        except Exception:
            logger.exception("Failed to create folio for booking %s", booking_id)

    return {"booking_id": booking_id, "stay_status": "checked_in", "folio": folio,
            "folio_number": folio_id, "invoice_id": invoice_id}
