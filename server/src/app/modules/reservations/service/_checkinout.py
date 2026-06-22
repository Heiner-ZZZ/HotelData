from __future__ import annotations

from typing import Any

from src.database.connection import get_database

from ._helpers import CHECKIN_COMPLETED_STATUSES, CHECKOUT_COMPLETED_STATUSES, utc_now
from ._history_lookup import _booking_history_lookup, _derived_stay_status


def complete_check_in(booking_id: str, *, changed_by: str = "angular_api") -> dict[str, Any]:
    db = get_database()
    changed_at = utc_now()
    result = db.booking_orders.find_one_and_update(
        {"booking_id": booking_id, "status": {"$nin": ["cancelled", "rejected"]}, "stay_status": {"$ne": "checked_in"}},
        {"$set": {"stay_status": "checked_in", "updated_at": changed_at}},
        projection={"_id": 0, "is_test": 1, "total_price": 1, "currency": 1},
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

    # --- GAP-046: Auto-create invoice for non-test bookings at check-in ---
    invoice_id: str | None = None
    if not result.get("is_test"):
        total = result.get("total_price")
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
                pass

    return {"booking_id": booking_id, "stay_status": "checked_in", "invoice_id": invoice_id}


def complete_check_out(booking_id: str, *, changed_by: str = "angular_api") -> dict[str, Any]:
    db = get_database()
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
    return {"booking_id": booking_id, "stay_status": "checked_out"}
