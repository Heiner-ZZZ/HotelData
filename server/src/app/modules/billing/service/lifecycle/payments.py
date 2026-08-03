"""Payment CRUD operations."""

from __future__ import annotations

import logging
import secrets

from bson import ObjectId
from pymongo import ReturnDocument

from src.database.connection import get_database

logger = logging.getLogger(__name__)
from src.app.core.resolvers import resolve_hotel_id
from src.app.core.state_machine import payment_sm
from src.app.modules.billing.schemas import PaymentCreate
from src.app.modules.billing.service.lifecycle._helpers import (
    _enrich_payment,
    _find_booking,
    _now,
    _update_both,
    _write_both,
    FACT_INVOICES,
    FACT_PAYMENTS,
    INVOICES,
    PAYMENTS,
)


def create_payment(payload: PaymentCreate) -> dict | None:
    db = get_database()
    booking = _find_booking(payload.booking_id)
    if not booking:
        return None
    invoice_id = None
    if payload.invoice_id:
        inv = db[INVOICES].find_one({"_id": ObjectId(payload.invoice_id)})
        if inv:
            invoice_id = ObjectId(payload.invoice_id)

    # Un gateway puede registrar intentos fallidos/rechazados; esos pagos NO
    # marcan la factura como pagada (solo ``confirmed`` lo hace).
    status = (payload.status or "confirmed").strip().lower()
    if status not in {"confirmed", "failed", "rejected", "declined", "error"}:
        status = "confirmed"

    doc = {
        "booking_id": booking.get("booking_id") or payload.booking_id,
        "prop_id": booking.get("prop_id", 0),
        "hotel_id": resolve_hotel_id(booking.get("prop_id", 0)),
        "invoice_id": invoice_id,
        "amount": round(payload.amount, 2),
        "method": payload.method,
        "status": status,
        "reference": f"PAY-{secrets.token_hex(6).upper()}",
        "paid_at": _now(),
    }
    _write_both(PAYMENTS, FACT_PAYMENTS, doc)

    # Generate double-entry ledger entries for this payment (only when confirmed)
    if status == "confirmed":
        try:
            from src.app.modules.expenses.service.ledger_hooks import generate_ledger_from_payment
            generate_ledger_from_payment(doc)
        except Exception:
            logger.exception("Failed to generate ledger entries for payment %s", doc.get("reference", ""))

    if invoice_id and status == "confirmed":
        upd = {"$set": {"status": "paid", "paid_at": _now()}}
        _update_both(INVOICES, FACT_INVOICES, invoice_id, upd)

    doc["_id"] = doc.pop("_id", None)
    return _enrich_payment(doc)


def list_payments(
    booking_id: str | None = None,
    prop_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    db = get_database()
    query: dict = {}
    if prop_id:
        query["prop_id"] = prop_id
    if booking_id:
        booking = _find_booking(booking_id)
        booking_str_id = booking.get("booking_id") if booking else booking_id
        query["booking_id"] = booking_str_id
    total = db[PAYMENTS].count_documents(query)
    cursor = (
        db[PAYMENTS]
        .find(query)
        .sort("paid_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_payment(doc) for doc in cursor]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def get_payment(payment_id: str) -> dict | None:
    db = get_database()
    try:
        from bson.errors import InvalidId
        doc = db[PAYMENTS].find_one({"_id": ObjectId(payment_id)})
    except (InvalidId, Exception):
        return None
    return _enrich_payment(doc) if doc else None


def refund_payment(payment_id: str) -> dict | None:
    db = get_database()
    try:
        from bson.errors import InvalidId
        pay_id = ObjectId(payment_id)
    except (InvalidId, Exception):
        return None

    existing_pay = db[PAYMENTS].find_one({"_id": pay_id}, {"status": 1})
    if not existing_pay:
        return None

    # Validate with central StateMachine
    try:
        payment_sm.validate_transition(existing_pay.get("status", ""), "refunded")
    except ValueError:
        return None

    pay = db[PAYMENTS].find_one_and_update(
        {"_id": pay_id, "status": existing_pay["status"]},
        {"$set": {"status": "refunded", "updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )
    if pay:
        _update_both(PAYMENTS, FACT_PAYMENTS, pay_id, {"$set": {"status": "refunded", "updated_at": _now()}})
        if pay.get("invoice_id"):
            inv_id = pay["invoice_id"]
            upd = {"$set": {"status": "refunded", "updated_at": _now()}}
            _update_both(INVOICES, FACT_INVOICES, inv_id, upd)
    return _enrich_payment(pay) if pay else None
