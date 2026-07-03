"""Shared helpers for billing lifecycle operations."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from bson import ObjectId

from src.database.connection import get_database

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
    """Generate sequential invoice number: INV-YYYYMM-XXXX where XXXX is sequential per month."""
    db = get_database()
    prefix = f"INV-{_now().strftime('%Y%m')}-"
    last = db[INVOICES].find_one(
        {"invoice_number": {"$regex": f"^{prefix}"}},
        sort=[("invoice_number", -1)],
        projection={"invoice_number": 1},
    )
    if last and last.get("invoice_number"):
        try:
            seq = int(last["invoice_number"].split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def _find_booking(booking_id: str) -> dict | None:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        try:
            booking = db.booking_orders.find_one({"_id": ObjectId(booking_id)})
        except Exception:
            pass
    return booking


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
