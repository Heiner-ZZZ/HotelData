"""Check-out operations."""

from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId

from src.database.connection import get_database
from .._helpers import utc_now
from src.app.modules.reservations.service._checkinout._helpers import (
    _notify_guest_check_out,
    _notify_staff_check_out,
)
from .._transitions import _restore_inventory
from src.app.modules.partner.services.audit import register_action

logger = logging.getLogger(__name__)


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
    shift_id: str | None = None,
) -> dict[str, Any]:
    # ── Validate keys_returned BEFORE any database writes ──
    if not keys_returned:
        raise ValueError(
            "No se puede completar el check-out sin registrar la devolución de llaves. "
            "Marca 'Llaves devueltas' en el paso de verificación antes de cerrar la estancia."
        )

    db = get_database()

    # ── Validate folio has invoice if balance is pending ──
    folio = db.guest_folios.find_one(
        {"booking_id": booking_id},
        {"status": 1, "total_due": 1, "folio_number": 1},
    )
    if folio:
        folio_status = folio.get("status", "")
        total_due = round(float(folio.get("total_due", 0) or 0), 2)
        if folio_status == "open" and total_due > 0:
            existing_inv = db.reservation_invoices.find_one({"booking_id": booking_id}, {"_id": 1})
            if not existing_inv:
                raise ValueError(
                    f"No se puede completar el check-out: el folio {folio.get('folio_number', '')} "
                    f"tiene un saldo pendiente de ${total_due:.2f} sin factura generada. "
                    "Registra un pago para generar la factura antes de cerrar la estancia."
                )

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "guest_name": 1, "guest_email": 1, "prop_id": 1, "is_test": 1,
         "check_in_date": 1, "check_out_date": 1, "total_price": 1, "currency": 1,
         "total_nights": 1, "rooms": 1, "room_type_id": 1, "assigned_rooms": 1,
         "check_out_room_inspected": 1, "check_out_keys_returned": 1},
    )

    changed_at = utc_now()

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
    if shift_id:
        # Front-desk check-outs are tied to the open cash shift at write time.
        checkout_set["shift_id"] = ObjectId(shift_id)

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

    audit_entry: dict[str, Any] = {
        "booking_id": booking_id, "status": "checked_out",
        "changed_at": changed_at, "reason": "front_desk_check_out",
        "changed_by": changed_by, "is_test": bool(result.get("is_test")),
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

    # ── Audit log (universal) ──
    if booking and not booking.get("is_test"):
        try:
            register_action(
                prop_id=int(booking.get("prop_id", 0)),
                entity_type="reservation",
                entity_id=booking_id,
                action="check_out",
                summary=f"Check-out completado — {booking.get('guest_name', '')}",
                changed_by=changed_by,
                metadata={"guest_name": booking.get("guest_name", ""),
                         "payment_method": payment_method,
                         "observations": observations,
                         "damages_found": damages_found,
                         "keys_returned": keys_returned},
            )
        except Exception:
            logger.exception("Failed to register audit action for check-out %s", booking_id)

    # ── Notifications ──
    if booking:
        _notify_guest_check_out(booking_id, booking)
        if not booking.get("is_test"):
            _notify_staff_check_out(booking_id, booking)

    # ── Restore inventory ──
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

    # ── Settle additional charges ──
    if booking and not booking.get("is_test"):
        try:
            if split_invoice:
                from src.app.modules.billing.service import create_split_charges_invoice
                charges_inv = create_split_charges_invoice(booking_id, changed_by=changed_by)
                if charges_inv:
                    logger.info("Split invoice created for booking %s", booking_id)
                else:
                    logger.info("No additional charges to split-invoice for booking %s", booking_id)
            else:
                from src.app.modules.billing.service import update_invoice_additional_charges
                settled = update_invoice_additional_charges(booking_id, changed_by=changed_by)
                if settled:
                    logger.info("Liquidated charges for booking %s", booking_id)
                else:
                    logger.info("No invoice found to settle charges for booking %s", booking_id)
        except Exception:
            logger.exception("Failed to settle additional charges on check-out for booking %s", booking_id)

    # ── Mark rooms as dirty + auto-create cleaning tasks ──
    if booking:
        try:
            assigned_rooms_co: list[str] = booking.get("assigned_rooms") or []
            if assigned_rooms_co:
                room_docs_co = list(
                    db.hotel_rooms.find(
                        {"hotel_room_id": {"$in": assigned_rooms_co}},
                        {"_id": 1, "hotel_room_id": 1, "room_label": 1, "room_type_id": 1},
                    )
                )
                for r in room_docs_co:
                    label = r.get("room_label", "")
                    if not label:
                        continue
                    db.room_status_log.update_one(
                        {"prop_id": booking["prop_id"], "room_label": label},
                        {"$set": {"status": "vacant_dirty", "note": f"Check-out: {booking_id}", "updated_at": changed_at},
                         "$setOnInsert": {"created_at": changed_at}},
                        upsert=True,
                    )
                    db.housekeeping_tasks.insert_one({
                        "prop_id": booking["prop_id"],
                        "room_id": r["_id"],
                        "hotel_room_id": r.get("hotel_room_id", ""),
                        "room_label": label,
                        "room_type_id": r.get("room_type_id", ""),
                        "task_type": "cleaning",
                        "status": "pending",
                        "assigned_to": "",
                        "priority": "normal",
                        "note": f"Limpieza automática post check-out — reserva {booking_id}",
                        "scheduled_date": "",
                        "created_at": utc_now(),
                        "completed_at": None,
                    })
                logger.info("Rooms marked as dirty + cleaning tasks created for booking %s", booking_id)
        except Exception:
            logger.exception("Failed to mark rooms as dirty for booking %s", booking_id)

    # ── Register shift transaction ──
    if booking and not booking.get("is_test"):
        try:
            from src.app.modules.reception import register_transaction
            # Use folio total_due (room + charges - discounts - payments) instead of
            # booking.total_price which only reflects the original room rate.
            total_due = round(float(folio.get("total_due", 0) or 0), 2) if folio else float(booking.get("total_price", 0) or 0)
            register_transaction(
                prop_id=int(booking.get("prop_id", 0)),
                txn_type="check_out", booking_id=booking_id,
                amount=total_due, payment_method=payment_method or "",
                description=f"Check-out: {booking.get('guest_name', '')} — ${total_due:.2f}",
            )
        except Exception:
            logger.exception("Failed to register shift transaction for check-out %s", booking_id)

    # ── Close folio ──
    if booking and not booking.get("is_test"):
        try:
            from src.app.modules.billing.service import close_folio
            inv_doc = db.reservation_invoices.find_one({"booking_id": booking_id}, {"_id": 1})
            inv_id = str(inv_doc["_id"]) if inv_doc else None
            close_folio(booking_id, invoice_id=inv_id, closed_by=changed_by)
            logger.info("Folio closed for booking %s on check-out", booking_id)
        except Exception:
            logger.exception("Failed to close folio on check-out for booking %s", booking_id)

    # ── Notify guest about invoice ──
    if booking and not booking.get("is_test"):
        try:
            guest_email = (booking.get("guest_email") or "").strip()
            if guest_email:
                from src.app.modules.reservations.notifications import notify_guest_invoice
                inv = db.reservation_invoices.find_one(
                    {"booking_id": booking_id},
                    {"_id": 1, "invoice_number": 1, "total": 1},
                )
                if inv:
                    notify_guest_invoice(
                        booking_id=booking_id, guest_name=booking.get("guest_name", ""),
                        guest_email=guest_email, prop_id=int(booking.get("prop_id", 0)),
                        check_in_date=booking.get("check_in_date", ""),
                        check_out_date=booking.get("check_out_date", ""),
                        total_nights=int(booking.get("total_nights", 0)),
                        invoice_id=str(inv["_id"]), invoice_number=inv.get("invoice_number", ""),
                        invoice_total=float(inv.get("total", 0)), currency=booking.get("currency", "USD"),
                    )
        except Exception:
            logger.exception("Failed to notify guest about invoice on check-out for booking %s", booking_id)

    # ── Deactivate stay session ──
    if booking and not booking.get("is_test"):
        try:
            result_sess = db.stay_sessions.update_many(
                {"booking_id": booking_id, "active": True},
                {"$set": {"active": False, "deactivated_at": changed_at}},
            )
            if result_sess.modified_count > 0:
                logger.info("Stay session deactivated for booking %s on check-out", booking_id)
        except Exception:
            logger.exception("Failed to deactivate stay session for booking %s", booking_id)

    return {"booking_id": booking_id, "stay_status": "checked_out"}
