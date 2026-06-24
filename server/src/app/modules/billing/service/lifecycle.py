from __future__ import annotations

import secrets
from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ReturnDocument

from src.database.connection import get_database
from src.app.modules.billing.schemas import InvoiceCreate, PaymentCreate

INVOICES = "reservation_invoices"
PAYMENTS = "reservation_payments"
FACT_INVOICES = "fact_reservation_invoices"
FACT_PAYMENTS = "fact_reservation_payments"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _write_both(collection: str, fact_collection: str, doc: dict) -> None:
    db = get_database()
    result = db[collection].insert_one(doc)
    fact_doc = {**doc, "operational_id": result.inserted_id, "_id": result.inserted_id}
    db[fact_collection].insert_one(fact_doc)


def _update_both(collection: str, fact_collection: str, doc_id: ObjectId, update: dict) -> None:
    db = get_database()
    db[collection].update_one({"_id": doc_id}, update)
    db[fact_collection].update_one({"_id": doc_id}, update)


def _generate_invoice_number() -> str:
    return f"INV-{_now().strftime('%Y%m')}-{secrets.token_hex(4).upper()}"


# --- Invoices ---

# --- Invoices ---

def _find_booking(booking_id: str) -> dict | None:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        try:
            booking = db.booking_orders.find_one({"_id": ObjectId(booking_id)})
        except Exception:
            pass
    return booking


def generate_invoice_for_booking(booking_id: str, total_price: float | None = None, currency: str = "USD", notes: str = "") -> dict | None:
    """Auto-generate an invoice for a booking when confirmed.

    Calculates subtotal and taxes (IVA 16%) from the total_price.
    If total_price is None/0, attempts to look it up from the booking.
    """
    booking = _find_booking(booking_id)
    if not booking:
        return None

    price = total_price if total_price else booking.get("total_price")
    if not price:
        price = 0.0
    price = float(price)
    subtotal = round(price / 1.16, 2)
    taxes = round(price - subtotal, 2)

    payload = InvoiceCreate(
        booking_id=booking.get("booking_id") or booking_id,
        subtotal=subtotal,
        taxes=taxes,
        notes=notes or f"Factura generada automaticamente por confirmacion de reserva {booking.get('booking_id', '')}"
    )
    return create_invoice(payload)


def create_invoice(payload: InvoiceCreate) -> dict | None:
    db = get_database()
    booking = _find_booking(payload.booking_id)
    if not booking:
        return None
    total = round(payload.subtotal + payload.taxes, 2)
    doc = {
        "booking_id": booking.get("booking_id") or payload.booking_id,
        "prop_id": booking.get("prop_id", 0),
        "invoice_number": _generate_invoice_number(),
        "subtotal": round(payload.subtotal, 2),
        "taxes": round(payload.taxes, 2),
        "total": total,
        "status": "issued",
        "notes": payload.notes or None,
        "issued_at": _now(),
        "paid_at": None,
    }
    _write_both(INVOICES, FACT_INVOICES, doc)
    doc["_id"] = doc.pop("_id", None)
    return _enrich_invoice(doc)


def list_invoices(
    booking_id: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    db = get_database()
    query: dict = {}
    if booking_id:
        # Match either string booking_id or check if it matches the object id of booking
        booking = _find_booking(booking_id)
        booking_str_id = booking.get("booking_id") if booking else booking_id
        query["booking_id"] = booking_str_id
    if status:
        query["status"] = status
    total = db[INVOICES].count_documents(query)
    cursor = (
        db[INVOICES]
        .find(query)
        .sort("issued_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_invoice(doc) for doc in cursor]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def get_invoice(invoice_id: str) -> dict | None:
    db = get_database()
    doc = db[INVOICES].find_one({"_id": ObjectId(invoice_id)})
    return _enrich_invoice(doc) if doc else None


def cancel_invoice(invoice_id: str) -> dict | None:
    db = get_database()
    doc_id = ObjectId(invoice_id)
    doc = db[INVOICES].find_one_and_update(
        {"_id": doc_id, "status": "issued"},
        {"$set": {"status": "cancelled", "updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        _update_both(INVOICES, FACT_INVOICES, doc_id, {"$set": {"status": "cancelled", "updated_at": _now()}})
    return _enrich_invoice(doc) if doc else None


# --- Payments ---

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

    doc = {
        "booking_id": booking.get("booking_id") or payload.booking_id,
        "prop_id": booking.get("prop_id", 0),
        "invoice_id": invoice_id,
        "amount": round(payload.amount, 2),
        "method": payload.method,
        "status": "confirmed",
        "reference": f"PAY-{secrets.token_hex(6).upper()}",
        "paid_at": _now(),
    }
    _write_both(PAYMENTS, FACT_PAYMENTS, doc)

    if invoice_id:
        upd = {"$set": {"status": "paid", "paid_at": _now()}}
        _update_both(INVOICES, FACT_INVOICES, invoice_id, upd)

    doc["_id"] = doc.pop("_id", None)
    return _enrich_payment(doc)


def list_payments(
    booking_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    db = get_database()
    query: dict = {}
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
    doc = db[PAYMENTS].find_one({"_id": ObjectId(payment_id)})
    return _enrich_payment(doc) if doc else None


def refund_payment(payment_id: str) -> dict | None:
    db = get_database()
    pay_id = ObjectId(payment_id)
    pay = db[PAYMENTS].find_one_and_update(
        {"_id": pay_id, "status": "confirmed"},
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


# --- Enrichment ---

def _fmt(val):
    if isinstance(val, datetime):
        return val.isoformat()
    return val


def _enrich_invoice(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    doc["booking_id"] = str(doc.get("booking_id", ""))
    for f in ("issued_at", "paid_at"):
        doc[f] = _fmt(doc.get(f))
    return doc


def _enrich_payment(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    doc["booking_id"] = str(doc.get("booking_id", ""))
    doc["invoice_id"] = str(doc["invoice_id"]) if doc.get("invoice_id") else None
    for f in ("paid_at",):
        doc[f] = _fmt(doc.get(f))
    return doc
