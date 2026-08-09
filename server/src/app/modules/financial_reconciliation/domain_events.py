"""Canonical hotel-scoped domain events and financial aggregate projection.

This is an application-level integration boundary for the modular monolith.
It does not make AR, operations, AP, or GL independent services; it gives them
one durable, idempotent event vocabulary and one rebuildable hotel projection.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import DuplicateKeyError

from src.app.core.outbox import write_with_outbox
from src.database.collections import ensure_collection
from src.database.connection import get_database

DOMAIN_EVENTS = "hotel_domain_events"
FACT_DOMAIN_EVENTS = "fact_hotel_domain_events"
AGGREGATES = "hotel_financial_aggregates"

_EVENT_INDEXES = [
    IndexModel(
        [("prop_id", ASCENDING), ("idempotency_key", ASCENDING)],
        name="idx_hotel_domain_event_prop_key",
        unique=True,
    ),
    IndexModel(
        [("prop_id", ASCENDING), ("occurred_at", DESCENDING)],
        name="idx_hotel_domain_event_prop_occurred",
    ),
    IndexModel(
        [("prop_id", ASCENDING), ("aggregate_type", ASCENDING), ("aggregate_id", ASCENDING)],
        name="idx_hotel_domain_event_aggregate",
    ),
]
_AGGREGATE_INDEXES = [
    IndexModel([("prop_id", ASCENDING)], name="idx_hotel_financial_aggregate_prop", unique=True),
]


def ensure_domain_event_collections() -> None:
    """Create the canonical event and aggregate collections/indexes."""
    ensure_collection(DOMAIN_EVENTS, _EVENT_INDEXES)
    ensure_collection(FACT_DOMAIN_EVENTS, _EVENT_INDEXES)
    ensure_collection(AGGREGATES, _AGGREGATE_INDEXES)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stable_event_id(prop_id: int, idempotency_key: str) -> str:
    digest = hashlib.sha256(f"{prop_id}:{idempotency_key}".encode()).hexdigest()[:20]
    return f"EVT-{digest}"


def append_domain_event(
    *,
    prop_id: int,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    idempotency_key: str,
    payload: dict[str, Any] | None = None,
    source_collection: str | None = None,
    source_id: str | None = None,
    actor_id: str | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
) -> dict[str, Any]:
    """Append one event exactly once for a hotel and idempotency key.

    The operational event and its fact mirror use the transactional outbox
    helper. Repeating the same key returns the committed event instead of
    producing another event or mirror row.
    """
    prop_id = int(prop_id)
    event_type = event_type.strip()
    aggregate_type = aggregate_type.strip()
    aggregate_id = str(aggregate_id).strip()
    idempotency_key = idempotency_key.strip()
    if prop_id < 1:
        raise ValueError("prop_id debe ser positivo")
    if not event_type or not aggregate_type or not aggregate_id or not idempotency_key:
        raise ValueError("event_type, aggregate_type, aggregate_id e idempotency_key son obligatorios")

    db = get_database()
    ensure_domain_event_collections()
    existing = db[DOMAIN_EVENTS].find_one({
        "prop_id": prop_id,
        "idempotency_key": idempotency_key,
    })
    if existing:
        return existing

    now = _now()
    event = {
        "_id": ObjectId(),
        "event_id": _stable_event_id(prop_id, idempotency_key),
        "event_version": 1,
        "prop_id": prop_id,
        "event_type": event_type,
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id,
        "idempotency_key": idempotency_key,
        "payload": payload or {},
        "source_collection": source_collection,
        "source_id": str(source_id) if source_id is not None else None,
        "actor_id": actor_id,
        "correlation_id": correlation_id,
        "causation_id": causation_id,
        "occurred_at": now,
        "created_at": now,
    }
    try:
        write_with_outbox(db, DOMAIN_EVENTS, event, FACT_DOMAIN_EVENTS)
    except DuplicateKeyError:
        committed = db[DOMAIN_EVENTS].find_one({
            "prop_id": prop_id,
            "idempotency_key": idempotency_key,
        })
        if committed:
            return committed
        raise
    return event


def _sum_documents(cursor, field: str) -> float:
    return round(sum(float(doc.get(field, 0) or 0) for doc in cursor), 2)


def _event_counts(db: Any, prop_id: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in db[DOMAIN_EVENTS].find({"prop_id": prop_id}, {"aggregate_type": 1}):
        key = str(row.get("aggregate_type") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def backfill_domain_events(prop_id: int) -> dict[str, int]:
    """Project existing hotel documents into the canonical event stream.

    This is a documentary backfill only: it never changes source documents,
    balances, statuses, invoices, payments, or ledger rows. Stable source IDs
    make the operation safe to rerun and keep another hotel out of the stream.
    """
    prop_id = int(prop_id)
    if prop_id < 1:
        raise ValueError("prop_id debe ser positivo")
    db = get_database()
    ensure_domain_event_collections()
    created = 0
    existing = 0

    def project(collection: str, event_type: str, aggregate_type: str, projection: dict[str, int], id_field: str = "_id") -> None:
        nonlocal created, existing
        for source in db[collection].find({"prop_id": prop_id}, projection):
            source_id = str(source.get(id_field))
            idempotency_key = f"backfill:v1:{collection}:{source_id}"
            was_existing = db[DOMAIN_EVENTS].find_one({
                "prop_id": prop_id,
                "idempotency_key": idempotency_key,
            }, {"_id": 1}) is not None
            append_domain_event(
                prop_id=prop_id,
                event_type=event_type.format(status=str(source.get("status") or "unknown")),
                aggregate_type=aggregate_type,
                aggregate_id=source_id,
                idempotency_key=idempotency_key,
                payload={
                    key: value for key, value in source.items()
                    if key not in {"_id", "prop_id"}
                },
                source_collection=collection,
                source_id=source_id,
            )
            if was_existing:
                existing += 1
            else:
                created += 1

    project("reservation_invoices", "guest_ar.invoice.{status}", "guest_ar", {"_id": 1, "status": 1, "total": 1})
    project("reservation_payments", "guest_ar.payment.{status}", "guest_ar", {"_id": 1, "status": 1, "amount": 1})
    project("guest_folios", "guest_ar.folio.{status}", "guest_ar", {"_id": 1, "status": 1, "total_due": 1})
    project("additional_charges", "operations.additional_charge.{status}", "operations", {"_id": 1, "status": 1, "posting_status": 1, "total": 1})
    project("maintenance_tasks", "operations.maintenance.{status}", "operations", {"_id": 1, "status": 1, "actual_cost": 1})
    project("expense_invoices", "vendor_ap.invoice.{status}", "vendor_ap", {"_id": 1, "status": 1, "total": 1})
    project("ledger_transactions", "general_ledger.posting", "general_ledger", {"_id": 1, "source": 1, "source_id": 1, "debit": 1, "credit": 1})

    return {"prop_id": prop_id, "created": created, "existing": existing}


def rebuild_hotel_financial_aggregate(prop_id: int) -> dict[str, Any]:
    """Rebuild the hotel projection exclusively from hotel-scoped Mongo data.

    Rebuilding is deterministic and safe to repeat. The projection is a read
    model, never the source of truth; deleting it and calling this function
    reconstructs the same AR/AP/operations/GL totals.
    """
    prop_id = int(prop_id)
    if prop_id < 1:
        raise ValueError("prop_id debe ser positivo")
    db = get_database()
    ensure_domain_event_collections()

    invoice_docs = db.reservation_invoices.find({
        "prop_id": prop_id,
        "status": {"$nin": ["cancelled", "refunded"]},
    }, {"total": 1})
    invoiced = _sum_documents(invoice_docs, "total")

    confirmed_payments = list(db.reservation_payments.find({
        "prop_id": prop_id,
        "status": "confirmed",
    }, {"amount": 1}))
    refunded_payments = list(db.reservation_payments.find({
        "prop_id": prop_id,
        "status": "refunded",
    }, {"amount": 1}))
    confirmed_total = round(sum(float(row.get("amount", 0) or 0) for row in confirmed_payments), 2)
    refunded_total = round(sum(float(row.get("amount", 0) or 0) for row in refunded_payments), 2)
    net_collected = round(confirmed_total - refunded_total, 2)

    outstanding_folios = _sum_documents(db.guest_folios.find({
        "prop_id": prop_id,
        "total_due": {"$gt": 0},
    }, {"total_due": 1}), "total_due")

    maintenance_cost = _sum_documents(db.maintenance_tasks.find({
        "prop_id": prop_id,
        "status": {"$ne": "deleted"},
    }, {"actual_cost": 1}), "actual_cost")

    approved_expenses = _sum_documents(db.expense_invoices.find({
        "prop_id": prop_id,
        "status": {"$in": ["approved", "paid"]},
    }, {"total": 1}), "total")
    paid_expenses = _sum_documents(db.expense_invoices.find({
        "prop_id": prop_id,
        "status": "paid",
    }, {"total": 1}), "total")

    ledger_rows = list(db.ledger_transactions.find({
        "prop_id": prop_id,
    }, {"debit": 1, "credit": 1}))
    ledger_debit = round(sum(float(row.get("debit", 0) or 0) for row in ledger_rows), 2)
    ledger_credit = round(sum(float(row.get("credit", 0) or 0) for row in ledger_rows), 2)
    ledger_difference = round(ledger_debit - ledger_credit, 2)

    existing = db[AGGREGATES].find_one({"prop_id": prop_id}, {"_id": 1})
    now = _now()
    aggregate = {
        "prop_id": prop_id,
        "projection_version": 1,
        "rebuilt_at": now,
        "guest_ar": {
            "invoiced": invoiced,
            "collected": confirmed_total,
            "refunded": refunded_total,
            "net_collected": net_collected,
            "outstanding_folios": outstanding_folios,
            "confirmed_payment_count": len(confirmed_payments),
            "refunded_payment_count": len(refunded_payments),
        },
        "operations": {
            "maintenance_cost": maintenance_cost,
        },
        "vendor_ap": {
            "approved": approved_expenses,
            "paid": paid_expenses,
            "unpaid": round(approved_expenses - paid_expenses, 2),
        },
        "general_ledger": {
            "debit": ledger_debit,
            "credit": ledger_credit,
            "difference": ledger_difference,
            "is_balanced": abs(ledger_difference) < 0.01,
            "transaction_count": len(ledger_rows),
        },
        "event_counts": _event_counts(db, prop_id),
        "source_counts": {
            "invoices": db.reservation_invoices.count_documents({"prop_id": prop_id}),
            "payments": db.reservation_payments.count_documents({"prop_id": prop_id}),
            "folios": db.guest_folios.count_documents({"prop_id": prop_id}),
            "maintenance": db.maintenance_tasks.count_documents({"prop_id": prop_id}),
            "expense_invoices": db.expense_invoices.count_documents({"prop_id": prop_id}),
            "ledger_transactions": len(ledger_rows),
        },
        "reconciliation_status": "ok" if abs(ledger_difference) < 0.01 else "warning",
    }
    if existing:
        aggregate["_id"] = existing["_id"]
    db[AGGREGATES].replace_one({"prop_id": prop_id}, aggregate, upsert=True)
    return aggregate


def get_hotel_financial_aggregate(prop_id: int) -> dict[str, Any] | None:
    """Return the stored projection without mixing another hotel's data."""
    db = get_database()
    return db[AGGREGATES].find_one({"prop_id": int(prop_id)})
