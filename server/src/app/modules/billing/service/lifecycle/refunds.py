"""Formal refund receipts and credit notes for billing reversals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from src.database.connection import get_database
from src.app.modules.billing.service.lifecycle._helpers import (
    FACT_INVOICES,
    FACT_PAYMENTS,
    INVOICES,
    PAYMENTS,
    _update_both,
    _now,
)

REFUND_DOCUMENTS = "refund_documents"
FACT_REFUND_DOCUMENTS = "fact_refund_documents"


def _document_number(db: Any, prefix: str) -> str:
    month = datetime.now(timezone.utc).strftime("%Y%m")
    base = f"{prefix}-{month}-"
    last = db[REFUND_DOCUMENTS].find_one(
        {"document_number": {"$regex": f"^{base}"}},
        sort=[("document_number", -1)],
        projection={"document_number": 1},
    )
    try:
        sequence = int(str(last["document_number"]).rsplit("-", 1)[-1]) + 1 if last else 1
    except (ValueError, KeyError):
        sequence = 1
    return f"{base}{sequence:04d}"


def _enrich_document(doc: dict | None) -> dict | None:
    if not doc:
        return None
    result = dict(doc)
    result["id"] = str(result.pop("_id"))
    for field in ("payment_id", "invoice_id", "original_invoice_id"):
        if result.get(field) is not None:
            result[field] = str(result[field])
    for field in ("issued_at", "updated_at"):
        value = result.get(field)
        if isinstance(value, datetime):
            result[field] = value.isoformat()
    return result


def _balanced_journal(db: Any, source: str, source_id: str) -> tuple[bool, str | None]:
    rows = list(db.ledger_transactions.find(
        {"source": source, "source_id": source_id},
        {"debit": 1, "credit": 1, "journal_entry_id": 1},
    ))
    debit = round(sum(float(row.get("debit", 0) or 0) for row in rows), 2)
    credit = round(sum(float(row.get("credit", 0) or 0) for row in rows), 2)
    journals = sorted({str(row.get("journal_entry_id")) for row in rows if row.get("journal_entry_id")})
    return len(rows) >= 2 and debit > 0 and debit == credit, (journals[0] if journals else None)


def _mirror_document(db: Any, document: dict) -> None:
    mirror = dict(document)
    db[FACT_REFUND_DOCUMENTS].replace_one({"_id": document["_id"]}, mirror, upsert=True)


def _link_payment(db: Any, payment: dict, document: dict, *, refund_id: str | None) -> None:
    payment_update: dict[str, Any] = {
        "refund_document_id": document["_id"],
        "refund_document_number": document["document_number"],
        "updated_at": _now(),
    }
    if refund_id and not payment.get("refund_id"):
        payment_update["refund_id"] = refund_id
    _update_both(PAYMENTS, FACT_PAYMENTS, payment["_id"], {"$set": payment_update})
    refreshed = db[PAYMENTS].find_one({"_id": payment["_id"]})
    if refreshed:
        db[FACT_PAYMENTS].replace_one({"_id": payment["_id"]}, dict(refreshed), upsert=True)


def _record_refund_reconciliation_trace(
    db: Any,
    payment: dict[str, Any],
    document: dict[str, Any],
    *,
    event_id: str,
    changed_by: str,
) -> None:
    """Record the legacy refund repair in the canonical event and audit trails."""
    payment_id = str(payment["_id"])
    document_id = str(document.get("id") or document.get("_id") or "")
    idempotency_key = f"refund-reconciliation:v1:{payment_id}:{event_id}"
    from src.app.modules.financial_reconciliation.domain_events import append_domain_event
    from src.app.modules.partner.services.audit import register_action

    event = append_domain_event(
        prop_id=int(payment.get("prop_id", 0) or 0),
        event_type="guest_ar.payment_refund.reconciled",
        aggregate_type="guest_ar",
        aggregate_id=payment_id,
        idempotency_key=idempotency_key,
        payload={
            "payment_id": payment_id,
            "booking_id": str(payment.get("booking_id") or ""),
            "refund_document_id": document_id,
            "refund_document_number": document.get("document_number"),
            "invoice_id": str(document.get("invoice_id")) if document.get("invoice_id") else None,
            "amount": round(float(payment.get("amount", 0) or 0), 2),
            "method": payment.get("method"),
            "repair_type": "legacy_refund_reconciliation",
        },
        source_collection=PAYMENTS,
        source_id=payment_id,
        actor_id=changed_by,
    )
    if not db.audit_log.find_one({
        "prop_id": int(payment.get("prop_id", 0) or 0),
        "entity_type": "refund_reconciliation",
        "entity_id": payment_id,
        "metadata.idempotency_key": idempotency_key,
    }, {"_id": 1}):
        register_action(
            prop_id=int(payment.get("prop_id", 0) or 0),
            entity_type="refund_reconciliation",
            entity_id=payment_id,
            action="backfill",
            summary=f"Reconciliación de reembolso legacy {document.get('document_number', document_id)}",
            changed_by=changed_by,
            diff={
                "refund_document_id": {"old": None, "new": document_id},
                "refund_ledger": {"old": False, "new": True},
            },
            metadata={
                "idempotency_key": idempotency_key,
                "domain_event_id": event.get("event_id"),
                "payment_id": payment_id,
                "refund_document_id": document_id,
                "refund_document_number": document.get("document_number"),
                "refund_id": event_id,
            },
        )


def _record_payment_reconciliation_classification(
    db: Any,
    payment: dict[str, Any],
    document: dict[str, Any],
    *,
    refund_id: str,
    changed_by: str,
    invoice_backed: bool,
    zero_value_invoice: bool = False,
) -> None:
    """Persist the explicit applied/unapplied refund classification once."""
    payment_id = payment["_id"]
    if invoice_backed:
        status = "applied_refund"
        reason = (
            "refunded_payment_with_zero_invoice_documented_receipt"
            if zero_value_invoice
            else "refunded_payment_with_invoice_documented_credit_note"
        )
        event_name = "classified_applied_refund"
    else:
        status = "unapplied_refund"
        reason = "refunded_payment_without_invoice_documented_receipt"
        event_name = "classified_unapplied_refund"

    now = _now()
    update = {
        "reconciliation_status": status,
        "reconciliation_reason": reason,
        "reconciliation_changed_by": changed_by,
        "reconciliation_changed_at": now,
        "updated_at": now,
    }
    _update_both(PAYMENTS, FACT_PAYMENTS, payment_id, {"$set": update})
    refreshed_payment = db[PAYMENTS].find_one({"_id": payment_id})
    if refreshed_payment:
        db[FACT_PAYMENTS].replace_one({"_id": payment_id}, dict(refreshed_payment), upsert=True)

    db.payment_reconciliation_events.update_one(
        {"payment_id": str(payment_id), "event": event_name},
        {"$setOnInsert": {
            "payment_id": str(payment_id),
            "prop_id": payment.get("prop_id", 0),
            "event": event_name,
            "reason": reason,
            "refund_id": refund_id,
            "refund_document_id": document.get("_id"),
            "refund_document_number": document.get("document_number"),
            "invoice_id": document.get("invoice_id"),
            "changed_by": changed_by,
            "changed_at": now,
        }},
        upsert=True,
    )


def create_credit_note_for_invoice(
    invoice_id: str,
    *,
    changed_by: str = "historical_reconciliation",
    payment_id: ObjectId | None = None,
    refund_id: str | None = None,
) -> dict | None:
    """Create or reuse the formal credit note for a cancelled/refunded invoice."""
    try:
        invoice_oid = ObjectId(invoice_id)
    except (InvalidId, TypeError):
        return None
    db = get_database()
    invoice = db[INVOICES].find_one({"_id": invoice_oid})
    invoice_status = str((invoice or {}).get("status", "")).lower()
    can_credit_paid_invoice = payment_id is not None and invoice_status in {"paid", "partially_paid"}
    if not invoice or (invoice_status not in {"cancelled", "refunded"} and not can_credit_paid_invoice):
        return None
    total = round(float(invoice.get("total", 0) or 0), 2)
    if total <= 0 or not invoice.get("invoice_number"):
        return None

    from src.app.modules.expenses.service.ledger_hooks import generate_reversal_from_invoice
    generate_reversal_from_invoice(invoice, db=db)
    balanced, journal_id = _balanced_journal(db, "invoice_reversal", str(invoice["invoice_number"]))
    if not balanced:
        return None

    now = _now()
    existing = db[REFUND_DOCUMENTS].find_one({
        "invoice_id": invoice_oid,
        "document_type": "credit_note",
    })
    if existing:
        update: dict[str, Any] = {"updated_at": now, "accounting_status": "posted"}
        if payment_id:
            update["payment_id"] = payment_id
        if refund_id:
            update["refund_id"] = refund_id
        db[REFUND_DOCUMENTS].update_one({"_id": existing["_id"]}, {"$set": update})
        existing = db[REFUND_DOCUMENTS].find_one({"_id": existing["_id"]})
    else:
        document = {
            "document_number": _document_number(db, "CN"),
            "document_type": "credit_note",
            "status": "issued",
            "payment_id": payment_id,
            "invoice_id": invoice_oid,
            "original_invoice_id": invoice_oid,
            "original_invoice_number": invoice.get("invoice_number"),
            "booking_id": invoice.get("booking_id", ""),
            "prop_id": invoice.get("prop_id", 0),
            "amount": total,
            "currency": invoice.get("currency", "USD"),
            "reason": "Reembolso o anulación de factura",
            "refund_id": refund_id,
            "ledger_source": "invoice_reversal",
            "ledger_source_id": invoice.get("invoice_number"),
            "ledger_journal_id": journal_id,
            "accounting_status": "posted",
            "issued_at": now,
            "issued_by": changed_by,
            "updated_at": now,
        }
        result = db[REFUND_DOCUMENTS].update_one(
            {"invoice_id": invoice_oid, "document_type": "credit_note"},
            {"$setOnInsert": {**document, "_id": ObjectId()}},
            upsert=True,
        )
        existing = db[REFUND_DOCUMENTS].find_one({"invoice_id": invoice_oid, "document_type": "credit_note"})

    if not existing:
        return None
    _mirror_document(db, existing)
    invoice_update = {
        "credit_note_id": existing["_id"],
        "credit_note_number": existing["document_number"],
        "original_total": total,
        "recognized_total": 0.0,
        "net_total": 0.0,
        "accounting_status": "reversed",
        "accounting_reversal_journal_id": journal_id,
        "updated_at": now,
    }
    db[INVOICES].update_one({"_id": invoice_oid}, {"$set": invoice_update})
    db[FACT_INVOICES].update_one({"_id": invoice_oid}, {"$set": invoice_update})
    if payment_id:
        payment = db[PAYMENTS].find_one({"_id": payment_id})
        if payment:
            _link_payment(db, payment, existing, refund_id=refund_id)
    return _enrich_document(existing)


def ensure_refund_document_for_payment(
    payment_id: str,
    *,
    changed_by: str = "historical_reconciliation",
) -> dict | None:
    """Ensure a refunded payment has a receipt or invoice-backed credit note."""
    try:
        payment_oid = ObjectId(payment_id)
    except (InvalidId, TypeError):
        return None
    db = get_database()
    payment = db[PAYMENTS].find_one({"_id": payment_oid})
    if not payment or str(payment.get("status", "")).lower() not in {"confirmed", "refunded"}:
        return None

    event_id = str(payment.get("refund_id") or payment.get("reference") or payment_id)
    balanced, _ = _balanced_journal(db, "payment_refund", event_id)
    if not balanced:
        from src.app.modules.expenses.service.ledger_hooks import post_journal_entry
        journal_id = post_journal_entry(
            amount=float(payment.get("amount", 0) or 0),
            dr_account_code="1030",
            dr_account_name="Cuentas por Cobrar Huéspedes",
            cr_account_code="1010",
            cr_account_name="Caja / Bancos",
            description=f"Reembolso formal {event_id}",
            prop_id=int(payment.get("prop_id", 0) or 0),
            source="payment_refund",
            source_id=event_id,
            booking_id=str(payment.get("booking_id") or ""),
        )
        balanced, _ = _balanced_journal(db, "payment_refund", event_id)
        if not balanced:
            return None

    invoice = None
    invoice_ref = payment.get("invoice_id")
    if invoice_ref:
        try:
            invoice = db[INVOICES].find_one({
                "_id": ObjectId(invoice_ref),
                "prop_id": int(payment.get("prop_id", 0) or 0),
                "booking_id": payment.get("booking_id"),
                "status": {"$in": ["cancelled", "refunded", "paid", "partially_paid"]},
            })
        except (InvalidId, TypeError):
            invoice = None

    if invoice:
        document = create_credit_note_for_invoice(
            str(invoice["_id"]),
            changed_by=changed_by,
            payment_id=payment_oid,
            refund_id=event_id,
        )
        if document:
            _record_payment_reconciliation_classification(
                db,
                db[PAYMENTS].find_one({"_id": payment_oid}) or payment,
                db[REFUND_DOCUMENTS].find_one({"_id": ObjectId(document["id"])}) or document,
                refund_id=event_id,
                changed_by=changed_by,
                invoice_backed=True,
            )
            _record_refund_reconciliation_trace(
                db,
                db[PAYMENTS].find_one({"_id": payment_oid}) or payment,
                document,
                event_id=event_id,
                changed_by=changed_by,
            )
            return document

    linked_invoice_id = invoice["_id"] if invoice else None
    now = _now()
    existing = db[REFUND_DOCUMENTS].find_one({"payment_id": payment_oid})
    if not existing:
        document = {
            "document_number": _document_number(db, "RF"),
            "document_type": "refund_receipt",
            "status": "issued",
            "payment_id": payment_oid,
            "invoice_id": linked_invoice_id,
            "original_invoice_id": linked_invoice_id,
            "original_invoice_number": invoice.get("invoice_number") if invoice else None,
            "booking_id": payment.get("booking_id", ""),
            "prop_id": payment.get("prop_id", 0),
            "amount": round(float(payment.get("amount", 0) or 0), 2),
            "currency": payment.get("currency", "USD"),
            "reason": "Reembolso de pago sin factura asociada",
            "refund_id": event_id,
            "ledger_source": "payment_refund",
            "ledger_source_id": event_id,
            "accounting_status": "posted",
            "issued_at": now,
            "issued_by": changed_by,
            "updated_at": now,
        }
        db[REFUND_DOCUMENTS].update_one(
            {"payment_id": payment_oid},
            {"$setOnInsert": {**document, "_id": ObjectId()}},
            upsert=True,
        )
        existing = db[REFUND_DOCUMENTS].find_one({"payment_id": payment_oid})
    if not existing:
        return None
    if linked_invoice_id and existing.get("invoice_id") != linked_invoice_id:
        db[REFUND_DOCUMENTS].update_one({"_id": existing["_id"]}, {"$set": {
            "invoice_id": linked_invoice_id,
            "original_invoice_id": linked_invoice_id,
            "original_invoice_number": invoice.get("invoice_number"),
            "reason": "Reembolso de pago asociado a factura de importe cero",
            "updated_at": _now(),
        }})
        existing = db[REFUND_DOCUMENTS].find_one({"_id": existing["_id"]})
    _mirror_document(db, existing)
    _link_payment(db, payment, existing, refund_id=event_id)
    payment = db[PAYMENTS].find_one({"_id": payment_oid}) or payment
    _record_payment_reconciliation_classification(
        db,
        payment,
        existing,
        refund_id=event_id,
        changed_by=changed_by,
        invoice_backed=linked_invoice_id is not None,
        zero_value_invoice=bool(invoice and float(invoice.get("total", 0) or 0) <= 0),
    )
    document = _enrich_document(existing)
    if document:
        _record_refund_reconciliation_trace(
            db,
            payment,
            document,
            event_id=event_id,
            changed_by=changed_by,
        )
    return document
