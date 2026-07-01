from __future__ import annotations

import logging
import secrets
import threading
from datetime import date, datetime
from typing import Any

from src.database.connection import get_database

from ..notifications import notify_guest_invoice, notify_guest_status_change, notify_staff_check_event
from ._helpers import CHECKIN_COMPLETED_STATUSES, CHECKOUT_COMPLETED_STATUSES, utc_now
from ._history_lookup import _booking_history_lookup, _derived_stay_status
from ._transitions import _restore_inventory


logger = logging.getLogger(__name__)


def update_check_in_datetime(
    booking_id: str,
    *,
    check_in_date: str | None = None,
    check_in_time: str | None = None,
    changed_by: str = "web",
) -> dict[str, Any]:
    """
    Update check-in date and/or time for an active booking.

    Unlike modify_booking, this works for both confirmed and checked_in bookings.
    """
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

    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": update_fields},
    )

    reason = f"check-in actualizado: {', '.join(reason_parts)}"
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": booking.get("status", "unknown"),
        "changed_at": now,
        "reason": reason,
        "changed_by": changed_by,
        "is_test": bool(booking.get("is_test", False)),
    })

    return {"booking_id": booking_id, "updated": True}


_CHECKIN_ALLOWED_ROOM_STATUSES = {"available", "vacant_clean", "vacant", "clean"}
_CHECKIN_REJECTED_STATUSES = {"dirty", "maintenance", "out_of_order", "out_of_service"}


def _generate_folio(prop_id: int) -> str:
    """Generate a unique folio number for a check-in.

    Format: FOL-{prop_id}-{YYMMDD}-{random4}
    """
    date_part = datetime.now().strftime("%y%m%d")
    random_part = secrets.token_hex(2).upper()
    return f"FOL-{prop_id}-{date_part}-{random_part}"


def complete_check_in(
    booking_id: str,
    *,
    changed_by: str = "web",
    payment_method: str = "",
    ip_address: str = "",
    observations: str = "",
) -> dict[str, Any]:
    db = get_database()

    # Fetch booking before update (need data for notification)
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
            check_in_date = date.fromisoformat(check_in_date_str)
            today = date.today()
            if check_in_date < today:
                raise ValueError(
                    f"No se puede realizar check-in para una fecha pasada. "
                    f"La fecha de check-in ({check_in_date_str}) es anterior a hoy ({today.isoformat()})."
                )
        except ValueError as exc:
            # Re-raise our own validation errors; pass through ValueError from date parsing
            if str(exc).startswith("No se puede"):
                raise
            logger.warning("Could not parse check_in_date '%s' for booking %s", check_in_date_str, booking_id)

    # ── Validate room status before allowing check-in ──
    assigned_rooms: list[str] = booking.get("assigned_rooms") or []
    _room_docs: list[dict[str, Any]] = []  # hoisted for reuse in status update + notification

    if assigned_rooms:
        # 1. Resolve hotel_room_id → room_label
        _room_docs = list(
            db.hotel_rooms.find(
                {"hotel_room_id": {"$in": assigned_rooms}},
                {"_id": 0, "hotel_room_id": 1, "room_label": 1, "room_number": 1},
            )
        )
        room_labels = {r["hotel_room_id"]: r.get("room_label", "") or r.get("room_number", "") for r in _room_docs}

        # 2. Look up room_status_log for each assigned room
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
                if status not in _CHECKIN_ALLOWED_ROOM_STATUSES:
                    number = label  # already the room_label/room_number
                    blocked.append(f"{number} ({status})")

            if blocked:
                raise ValueError(
                    f"No se puede realizar el check-in. Las siguientes habitaciones no están disponibles: "
                    f"{', '.join(blocked)}. Solo se permite check-in en habitaciones en estado 'available'. "
                    f"Estados rechazados: {', '.join(sorted(_CHECKIN_REJECTED_STATUSES))}."
                )

    changed_at = utc_now()
    folio = _generate_folio(int(booking.get("prop_id", 0)))
    now_iso = changed_at.isoformat()
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
        "booking_id": booking_id,
        "status": "checked_in",
        "changed_at": changed_at,
        "reason": "front_desk_check_in",
        "changed_by": changed_by,
        "is_test": bool(result.get("is_test")),
        "check_in_method": "manual",
    }
    if ip_address:
        audit_entry["ip_address"] = ip_address
    if observations:
        audit_entry["observations"] = observations
    db.booking_status_history.insert_one(audit_entry)

    # ── Notify guest on check-in (async — never block API response) ──
    if booking:
        guest_email = (booking.get("guest_email") or "").strip()
        if guest_email and not booking.get("is_test"):
            threading.Thread(
                target=_notify_guest_check_in,
                args=(booking_id, booking),
                daemon=True,
            ).start()

    # ── Notify staff on check-in (async) ──
    if booking and not booking.get("is_test"):
        threading.Thread(
            target=_notify_staff_check_in,
            args=(booking_id, booking),
            daemon=True,
        ).start()

    # ── Register transaction on active shift ──
    if booking and not booking.get("is_test"):
        try:
            from src.app.modules.reception import register_transaction
            register_transaction(
                prop_id=int(booking.get("prop_id", 0)),
                txn_type="check_in",
                booking_id=booking_id,
                description=f"Check-in: {booking.get('guest_name', '')} — Folio {folio}",
            )
        except Exception:
            logger.exception("Failed to register shift transaction for check-in %s", booking_id)

    # ── Auto-create or retrieve invoice on check-in ──
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
                        booking_id=booking_id,
                        subtotal=subtotal,
                        taxes=taxes,
                        notes=f"Auto-generated invoice for booking {booking_id} at check-in",
                    ))
                    if inv:
                        invoice_id = inv.get("id")
                except Exception:
                    # Invoice failure must never block check-in
                    logger.exception("Failed to auto-create invoice at check-in for booking %s", booking_id)

    # ── Mark assigned rooms as occupied in room_status_log ──
    if assigned_rooms and booking:
        try:
            for r in _room_docs:
                label = r.get("room_label", "") or r.get("room_number", "")
                if label:
                    db.room_status_log.update_one(
                        {"prop_id": booking["prop_id"], "room_label": label},
                        {
                            "$set": {
                                "status": "occupied_clean",
                                "note": f"Check-in: {booking_id}",
                                "updated_at": changed_at,
                            },
                            "$setOnInsert": {"created_at": changed_at},
                        },
                        upsert=True,
                    )
            logger.info(
                "Rooms marked as occupied for booking %s: %s",
                booking_id, [r.get("room_label", "") or r.get("room_number", "") for r in _room_docs],
            )
        except Exception:
            logger.exception("Failed to mark rooms as occupied for booking %s", booking_id)

    # ── Notify housekeeping about check-in ──
    if assigned_rooms and booking and not booking.get("is_test"):
        try:
            room_labels_str = ", ".join(
                r.get("room_label", "") or r.get("room_number", "")
                for r in _room_docs
            ) or str(len(assigned_rooms))
            db.notification_log.insert_one({
                "notification_type": "housekeeping_check_in",
                "entity_type": "booking",
                "entity_id": booking_id,
                "prop_id": booking["prop_id"],
                "recipient_email": "",
                "subject": f"Check-in: habitación(es) {room_labels_str} ocupadas",
                "message": (
                    f"El huésped {booking.get('guest_name', '')} ha realizado el check-in. "
                    f"Habitación(es): {room_labels_str}. "
                    f"Check-out: {booking.get('check_out_date', '')}."
                ),
                "status": "pending",
                "created_at": changed_at,
                "metadata": {
                    "booking_id": booking_id,
                    "assigned_rooms": assigned_rooms,
                    "guest_name": booking.get("guest_name", ""),
                    "check_out_date": booking.get("check_out_date", ""),
                },
            })
        except Exception:
            logger.exception("Failed to notify housekeeping for booking %s", booking_id)

    # ── Create folio (cuenta del huésped) ──
    folio_id: str | None = None
    if booking and not booking.get("is_test"):
        try:
            from src.app.modules.billing.service import create_folio
            folio_doc = create_folio(booking_id)
            if folio_doc:
                folio_id = folio_doc.get("folio_number")
                logger.info(
                    "Folio %s created for booking %s at check-in",
                    folio_id, booking_id,
                )
        except Exception:
            logger.exception("Failed to create folio for booking %s", booking_id)

    return {"booking_id": booking_id, "stay_status": "checked_in", "folio": folio, "folio_number": folio_id, "invoice_id": invoice_id}


def _notify_guest_check_in(booking_id: str, booking: dict[str, Any]) -> None:
    """Fire-and-forget: notify guest about check-in."""
    try:
        guest_email = (booking.get("guest_email") or "").strip()
        if guest_email:
            notify_guest_status_change(
                booking_id=booking_id,
                guest_name=booking.get("guest_name", ""),
                guest_email=guest_email,
                new_status="checked_in",
                prop_id=int(booking.get("prop_id", 0)),
                check_in_date=booking.get("check_in_date", ""),
                check_out_date=booking.get("check_out_date", ""),
                total_price=booking.get("total_price"),
                currency=booking.get("currency", "USD"),
                total_nights=int(booking.get("total_nights", 0)),
            )
    except Exception:
        logger.exception("Failed to notify guest on check-in for booking %s", booking_id)


def _notify_staff_check_in(booking_id: str, booking: dict[str, Any]) -> None:
    """Fire-and-forget: notify staff about check-in."""
    try:
        notify_staff_check_event(
            event_type="check_in",
            prop_id=int(booking.get("prop_id", 0)),
            booking_id=booking_id,
            guest_name=booking.get("guest_name", ""),
            check_in_date=booking.get("check_in_date", ""),
            check_out_date=booking.get("check_out_date", ""),
            total_nights=int(booking.get("total_nights", 0)),
        )
    except Exception:
        logger.exception("Failed to notify staff on check-in for booking %s", booking_id)


def complete_check_out(
    booking_id: str,
    *,
    changed_by: str = "web",
    split_invoice: bool = False,
    ip_address: str = "",
    observations: str = "",
    payment_method: str = "",
    payment_ref: str = "",
    late_checkout_fee: float = 0,
    discount: float = 0,
    discount_reason: str = "",
    damages_found: bool = False,
    keys_returned: bool = False,
) -> dict[str, Any]:
    # ── Validate keys_returned BEFORE any database writes ──
    if not keys_returned:
        raise ValueError(
            "No se puede completar el check-out sin registrar la devolución de llaves. "
            "Marca 'Llaves devueltas' en el paso de verificación antes de cerrar la estancia."
        )

    db = get_database()

    # Fetch booking before update (need data for notification)
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "guest_name": 1, "guest_email": 1, "prop_id": 1, "is_test": 1,
         "check_in_date": 1, "check_out_date": 1, "total_price": 1, "currency": 1,
         "total_nights": 1, "rooms": 1, "room_type_id": 1, "assigned_rooms": 1,
         "check_out_room_inspected": 1, "check_out_keys_returned": 1},
    )

    changed_at = utc_now()

    # Build the set fields dynamically, preserving other checkout detail if saved as draft
    checkout_set = {
        "stay_status": "checked_out",
        "updated_at": changed_at,
        "check_out_date_actual": changed_at.strftime("%Y-%m-%d"),
        "check_out_time_actual": changed_at.strftime("%H:%M"),
        "check_out_by": changed_by,
        "check_out_keys_returned": True,
    }
    if payment_method:
        checkout_set["check_out_payment_method"] = payment_method
    if payment_ref:
        checkout_set["check_out_payment_ref"] = payment_ref
    if late_checkout_fee:
        checkout_set["check_out_late_checkout_fee"] = round(late_checkout_fee, 2)
    if discount:
        checkout_set["check_out_discount"] = round(discount, 2)
    if discount_reason:
        checkout_set["check_out_discount_reason"] = discount_reason
    if damages_found:
        checkout_set["check_out_damages_found"] = True
    if observations:
        checkout_set["check_out_observations"] = observations

    result = db.booking_orders.find_one_and_update(
        {"booking_id": booking_id, "status": {"$nin": ["cancelled", "rejected"]}, "stay_status": "checked_in"},
        {"$set": checkout_set},
        projection={"_id": 0, "is_test": 1},
    )
    if result is None:
        existing = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0, "status": 1, "stay_status": 1})
        if existing is None:
            raise ValueError("booking not found")
        if existing.get("stay_status") == "checked_out":
            raise ValueError("booking already checked out")
        raise ValueError("booking cannot be checked out from current reservation status")
    # ── Enriched audit entry ──
    audit_entry: dict[str, Any] = {
        "booking_id": booking_id,
        "status": "checked_out",
        "changed_at": changed_at,
        "reason": "front_desk_check_out",
        "changed_by": changed_by,
        "is_test": bool(result.get("is_test")),
        "check_out_method": "manual",
    }
    if ip_address:
        audit_entry["ip_address"] = ip_address
    if observations:
        audit_entry["observations"] = observations
    if payment_method:
        audit_entry["payment_method"] = payment_method
    if payment_ref:
        audit_entry["payment_ref"] = payment_ref
    if late_checkout_fee:
        audit_entry["late_checkout_fee"] = round(late_checkout_fee, 2)
    if discount:
        audit_entry["discount"] = round(discount, 2)
        audit_entry["discount_reason"] = discount_reason
    if damages_found:
        audit_entry["damages_found"] = True
    db.booking_status_history.insert_one(audit_entry)

    # ── Notify guest on check-out ──
    if booking:
        try:
            guest_email = (booking.get("guest_email") or "").strip()
            if guest_email and not booking.get("is_test"):
                notify_guest_status_change(
                    booking_id=booking_id,
                    guest_name=booking.get("guest_name", ""),
                    guest_email=guest_email,
                    new_status="checked_out",
                    prop_id=int(booking.get("prop_id", 0)),
                    check_in_date=booking.get("check_in_date", ""),
                    check_out_date=booking.get("check_out_date", ""),
                    total_price=booking.get("total_price"),
                    currency=booking.get("currency", "USD"),
                    total_nights=int(booking.get("total_nights", 0)),
                )
        except Exception:
            logger.exception("Failed to notify guest on check-out for booking %s", booking_id)

    # ── Notify staff on check-out ──
    if booking and not booking.get("is_test"):
        try:
            notify_staff_check_event(
                event_type="check_out",
                prop_id=int(booking.get("prop_id", 0)),
                booking_id=booking_id,
                guest_name=booking.get("guest_name", ""),
                check_in_date=booking.get("check_in_date", ""),
                check_out_date=booking.get("check_out_date", ""),
                total_nights=int(booking.get("total_nights", 0)),
            )
        except Exception:
            logger.exception("Failed to notify staff on check-out for booking %s", booking_id)

    # ── Restore inventory on check-out ──
    if booking:
        try:
            _restore_inventory(
                prop_id=int(booking.get("prop_id", 0)),
                check_in_date=str(booking.get("check_in_date", "")),
                check_out_date=str(booking.get("check_out_date", "")),
                rooms=int(booking.get("rooms", 1)),
                room_type_id=str(booking.get("room_type_id", "")),
            )
            logger.info("Inventory restored for booking %s after check-out", booking_id)
        except Exception:
            logger.exception("Failed to restore inventory on check-out for booking %s", booking_id)

    # ── Settle additional charges on check-out ──
    if booking and not booking.get("is_test"):
        try:
            if split_invoice:
                # Split mode: create a separate invoice for charges only
                from src.app.modules.billing.service import create_split_charges_invoice
                charges_inv = create_split_charges_invoice(booking_id, changed_by=changed_by)
                if charges_inv:
                    charges_count = len(charges_inv.get("additional_charges", []) or [])
                    logger.info(
                        "Split invoice created for booking %s — charges invoice #%s ($%.2f) with %d item(s)",
                        booking_id, charges_inv.get("invoice_number", ""),
                        charges_inv.get("total", 0), charges_count,
                    )
                else:
                    logger.info("No additional charges to split-invoice for booking %s", booking_id)
            else:
                # Consolidated mode: merge charges into the room invoice
                from src.app.modules.billing.service import update_invoice_additional_charges
                settled = update_invoice_additional_charges(booking_id, changed_by=changed_by)
                if settled:
                    inv_total = settled.get("total", 0)
                    charges_count = len(settled.get("additional_charges", []) or [])
                    if charges_count:
                        logger.info(
                            "Liquidated %d additional charge(s) for booking %s — invoice total: $%.2f",
                            charges_count, booking_id, inv_total,
                        )
                    else:
                        logger.info("No additional charges found for booking %s at check-out", booking_id)
                else:
                    logger.info("No invoice found to settle charges for booking %s at check-out", booking_id)
        except Exception:
            logger.exception("Failed to settle additional charges on check-out for booking %s", booking_id)

    # ── Mark assigned rooms as dirty and auto-create cleaning tasks ──
    if booking:
        try:
            assigned_rooms_co: list[str] = booking.get("assigned_rooms") or []
            if assigned_rooms_co:
                room_docs_co = list(
                    db.hotel_rooms.find(
                        {"hotel_room_id": {"$in": assigned_rooms_co}},
                        {"_id": 0, "hotel_room_id": 1, "room_label": 1, "room_number": 1},
                    )
                )
                for r in room_docs_co:
                    label = r.get("room_label", "") or r.get("room_number", "")
                    if not label:
                        continue

                    # 1. Mark as vacant_dirty in room_status_log
                    db.room_status_log.update_one(
                        {"prop_id": booking["prop_id"], "room_label": label},
                        {
                            "$set": {
                                "status": "vacant_dirty",
                                "note": f"Check-out: {booking_id}",
                                "updated_at": changed_at,
                            },
                            "$setOnInsert": {"created_at": changed_at},
                        },
                        upsert=True,
                    )

                    # 2. Auto-create a cleaning task in housekeeping_tasks
                    hk_task = {
                        "prop_id": booking["prop_id"],
                        "room_label": label,
                        "task_type": "cleaning",
                        "status": "pending",
                        "assigned_to": "",
                        "priority": "normal",
                        "note": f"Limpieza automática post check-out — reserva {booking_id}",
                        "scheduled_date": "",
                        "created_at": utc_now(),
                        "completed_at": None,
                    }
                    db.housekeeping_tasks.insert_one(hk_task)

                logger.info(
                    "Rooms marked as dirty + cleaning tasks created for booking %s: %s",
                    booking_id, [r.get("room_label", "") or r.get("room_number", "") for r in room_docs_co],
                )
            else:
                logger.info("No assigned rooms to mark as dirty for booking %s", booking_id)
        except Exception:
            logger.exception("Failed to mark rooms as dirty / create cleaning tasks for booking %s", booking_id)

    # ── Register transaction on active shift ──
    if booking and not booking.get("is_test"):
        try:
            from src.app.modules.reception import register_transaction
            total_paid = float(booking.get("total_price", 0) or 0)
            register_transaction(
                prop_id=int(booking.get("prop_id", 0)),
                txn_type="check_out",
                booking_id=booking_id,
                amount=total_paid,
                payment_method=payment_method or "",
                description=f"Check-out: {booking.get('guest_name', '')} — ${total_paid:.2f}",
            )
        except Exception:
            logger.exception("Failed to register shift transaction for check-out %s", booking_id)

    # ── Close folio on check-out ──
    if booking and not booking.get("is_test"):
        try:
            from src.app.modules.billing.service import close_folio
            inv_doc = db.reservation_invoices.find_one(
                {"booking_id": booking_id},
                {"_id": 1},
            )
            inv_id = str(inv_doc["_id"]) if inv_doc else None
            close_folio(booking_id, invoice_id=inv_id, closed_by=changed_by)
            logger.info("Folio closed for booking %s on check-out", booking_id)
        except Exception:
            logger.exception("Failed to close folio on check-out for booking %s", booking_id)

    # ── Notify guest about invoice on check-out ──
    if booking and not booking.get("is_test"):
        try:
            guest_email = (booking.get("guest_email") or "").strip()
            if guest_email:
                inv = db.reservation_invoices.find_one(
                    {"booking_id": booking_id},
                    {"_id": 1, "invoice_number": 1, "total": 1},
                )
                if inv:
                    notify_guest_invoice(
                        booking_id=booking_id,
                        guest_name=booking.get("guest_name", ""),
                        guest_email=guest_email,
                        prop_id=int(booking.get("prop_id", 0)),
                        check_in_date=booking.get("check_in_date", ""),
                        check_out_date=booking.get("check_out_date", ""),
                        total_nights=int(booking.get("total_nights", 0)),
                        invoice_id=str(inv["_id"]),
                        invoice_number=inv.get("invoice_number", ""),
                        invoice_total=float(inv.get("total", 0)),
                        currency=booking.get("currency", "USD"),
                    )
        except Exception:
            logger.exception("Failed to notify guest about invoice on check-out for booking %s", booking_id)

    return {"booking_id": booking_id, "stay_status": "checked_out"}
