from __future__ import annotations

import logging
from typing import Any

from src.database.connection import get_database

from ..notifications import notify_guest_status_change, notify_staff_check_event
from ._helpers import CHECKIN_COMPLETED_STATUSES, CHECKOUT_COMPLETED_STATUSES, utc_now
from ._history_lookup import _booking_history_lookup, _derived_stay_status


logger = logging.getLogger(__name__)


def complete_check_in(booking_id: str, *, changed_by: str = "angular_api") -> dict[str, Any]:
    db = get_database()

    # Fetch booking before update (need data for notification)
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "guest_name": 1, "guest_email": 1, "prop_id": 1, "is_test": 1,
         "check_in_date": 1, "check_out_date": 1, "total_price": 1, "currency": 1, "total_nights": 1},
    )

    changed_at = utc_now()
    result = db.booking_orders.find_one_and_update(
        {"booking_id": booking_id, "status": {"$nin": ["cancelled", "rejected"]}, "stay_status": {"$ne": "checked_in"}},
        {"$set": {"stay_status": "checked_in", "updated_at": changed_at}},
        projection={"_id": 0, "is_test": 1},
    )
    if result is None:
        existing = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0, "status": 1, "stay_status": 1})
        if existing is None:
            raise ValueError("booking not found")
        if existing.get("stay_status") == "checked_in":
            raise ValueError("booking already checked in")
        raise ValueError("booking cannot be checked in from current reservation status")
    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": "checked_in",
            "changed_at": changed_at,
            "reason": "front_desk_check_in",
            "changed_by": changed_by,
            "is_test": bool(result.get("is_test")),
        }
    )

    # ── Notify guest on check-in ──
    if booking:
        try:
            guest_email = (booking.get("guest_email") or "").strip()
            if guest_email and not booking.get("is_test"):
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

    # ── Notify staff on check-in ──
    if booking and not booking.get("is_test"):
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

    return {"booking_id": booking_id, "stay_status": "checked_in", "invoice_id": invoice_id}


def complete_check_out(booking_id: str, *, changed_by: str = "angular_api") -> dict[str, Any]:
    db = get_database()

    # Fetch booking before update (need data for notification)
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "guest_name": 1, "guest_email": 1, "prop_id": 1, "is_test": 1,
         "check_in_date": 1, "check_out_date": 1, "total_price": 1, "currency": 1, "total_nights": 1},
    )

    changed_at = utc_now()
    result = db.booking_orders.find_one_and_update(
        {"booking_id": booking_id, "status": {"$nin": ["cancelled", "rejected"]}, "stay_status": "checked_in"},
        {"$set": {"stay_status": "checked_out", "updated_at": changed_at}},
        projection={"_id": 0, "is_test": 1},
    )
    if result is None:
        existing = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0, "status": 1, "stay_status": 1})
        if existing is None:
            raise ValueError("booking not found")
        if existing.get("stay_status") == "checked_out":
            raise ValueError("booking already checked out")
        raise ValueError("booking cannot be checked out from current reservation status")
    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": "checked_out",
            "changed_at": changed_at,
            "reason": "front_desk_check_out",
            "changed_by": changed_by,
            "is_test": bool(result.get("is_test")),
        }
    )

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

    return {"booking_id": booking_id, "stay_status": "checked_out"}
