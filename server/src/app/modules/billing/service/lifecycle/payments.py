"""Payment CRUD operations."""

from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime

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


def _valid_object_id(value: str) -> bool:
    """Whether a string is a valid Mongo ObjectId hex."""
    if not value:
        return False
    try:
        ObjectId(value)
        return True
    except Exception:
        return False


def _shift_attribution(shift_id: str) -> dict | None:
    """Denormalized cashier attribution of a shift (best-effort).

    Resolves the shift's employee/opener so money documents carry the
    responsible cashier without a join. Never raises: an unresolvable shift
    still leaves the ``shift_id`` FK on the document.
    """
    try:
        from src.app.modules.reception import get_shift_attribution
        attr = get_shift_attribution(shift_id)
        if not attr:
            return None
        return {
            key: attr[key]
            for key in ("shift_employee", "shift_opened_by", "shift_opened_by_id", "shift_type")
            if attr.get(key) is not None
        }
    except Exception:
        return None


def _emit_payment_domain_event(payment: dict) -> None:
    """Emit one canonical AR payment event without breaking legacy writes."""
    try:
        from src.app.modules.financial_reconciliation.domain_events import append_domain_event
        payment_id = payment.get("_id") or payment.get("id") or payment.get("reference", "")
        status = str(payment.get("status") or "unknown").lower()
        append_domain_event(
            prop_id=int(payment.get("prop_id", 0) or 0),
            event_type=f"guest_ar.payment.{status}",
            aggregate_type="guest_ar",
            aggregate_id=str(payment_id),
            idempotency_key=f"live:payment:{payment_id}:{status}",
            payload={
                "booking_id": payment.get("booking_id"),
                "amount": payment.get("amount", 0),
                "status": status,
                "evidence_type": payment.get("evidence_type"),
                "evidence_reference": payment.get("evidence_reference"),
                "actor_user_id": str(payment.get("actor_user_id")) if payment.get("actor_user_id") else None,
                "actor_username": payment.get("actor_username"),
            },
            source_collection=PAYMENTS,
            source_id=str(payment_id),
            actor_id=str(payment.get("actor_user_id")) if payment.get("actor_user_id") else payment.get("actor_username"),
        )
    except Exception:
        logger.exception("Failed to emit canonical payment domain event")


def create_payment(
    payload: PaymentCreate,
    *,
    shift_id: str | None = None,
    reference: str | None = None,
    paid_at: datetime | None = None,
    evidence_type: str | None = None,
    evidence_reference: str | None = None,
    payment_source: str | None = None,
    actor_user_id: ObjectId | None = None,
    actor_username: str | None = None,
) -> dict | None:
    db = get_database()
    booking = _find_booking(payload.booking_id)
    if not booking:
        return None
    invoice_id = None
    if payload.invoice_id:
        try:
            from bson.errors import InvalidId
            invoice_oid = ObjectId(payload.invoice_id)
        except InvalidId:
            raise ValueError("Factura inválida: invoice_id no es un ObjectId válido") from None
        inv = db[INVOICES].find_one({"_id": invoice_oid})
        if not inv:
            raise ValueError("Factura no encontrada")
        if (
            str(inv.get("booking_id")) != str(booking.get("booking_id") or payload.booking_id)
            or int(inv.get("prop_id", booking.get("prop_id", 0)) or 0) != int(booking.get("prop_id", 0) or 0)
        ):
            raise ValueError("La factura no pertenece a la reserva indicada")
        invoice_id = invoice_oid

    # Un gateway puede registrar intentos fallidos/rechazados; esos pagos NO
    # marcan la factura como pagada (solo ``confirmed`` lo hace).
    status = (payload.status or "confirmed").strip().lower()
    if status not in {"confirmed", "failed", "rejected", "declined", "error"}:
        status = "confirmed"

    if status == "confirmed":
        booking_key = booking.get("booking_id") or payload.booking_id
        open_folio = db.guest_folios.find_one(
            {"booking_id": booking_key, "status": "open"},
            {"total_due": 1},
        )
        if open_folio is not None:
            available_balance = float(open_folio.get("total_due", 0) or 0)
        else:
            # Online/pre-authorized payments may precede check-in, but they
            # still cannot exceed the immutable sold amount. Without this
            # guard, a pre-folio overpayment becomes a confirmed orphan that
            # reconciliation can no longer apply to the future folio.
            invoice_total = db[INVOICES].find_one(
                {"booking_id": booking_key, "status": {"$nin": ["cancelled", "refunded"]}},
                {"total": 1},
                sort=[("issued_at", -1)],
            )
            target_total = float((invoice_total or {}).get("total", 0) or 0)
            if target_total <= 0:
                target_total = float(booking.get("total_price", 0) or 0)
            # Some legacy callers create a payment before any price or invoice
            # exists. Preserve that compatibility; enforce the guard whenever
            # the system has a known monetary ceiling.
            if target_total > 0:
                paid_before = sum(
                    float(row.get("amount", 0) or 0)
                    for row in db[PAYMENTS].find(
                        {"booking_id": booking_key, "status": "confirmed"},
                        {"amount": 1},
                    )
                )
                available_balance = target_total - paid_before
            else:
                available_balance = None
        if available_balance is not None and round(float(payload.amount), 2) > round(available_balance, 2) + 0.01:
            raise ValueError("El pago excede el saldo pendiente")

    effective_paid_at = paid_at or _now()
    doc = {
        "booking_id": booking.get("booking_id") or payload.booking_id,
        "prop_id": booking.get("prop_id", 0),
        "hotel_id": resolve_hotel_id(booking.get("prop_id", 0)),
        "shift_id": ObjectId(shift_id) if shift_id else None,
        "invoice_id": invoice_id,
        "amount": round(payload.amount, 2),
        "method": payload.method,
        # Confirmed payments created before check-in remain confirmed and are
        # reconciled when the folio is created. When an open folio exists, the
        # status is downgraded to failed below if its atomic posting loses a
        # balance race or a required side effect fails.
        "status": status,
        "reference": reference or f"PAY-{secrets.token_hex(6).upper()}",
        "paid_at": effective_paid_at,
    }
    # The shift FK alone already ties the payment to the cashier; stamp the
    # employee/opener denormalized so reports don't need the join.
    if shift_id:
        attr = _shift_attribution(shift_id)
        if attr:
            doc.update(attr)
    if evidence_type:
        doc["evidence_type"] = evidence_type
    if evidence_reference:
        doc["evidence_reference"] = evidence_reference
    if payment_source:
        doc["payment_source"] = payment_source
    if actor_user_id:
        doc["actor_user_id"] = actor_user_id
    if actor_username:
        doc["actor_username"] = actor_username
    _write_both(PAYMENTS, FACT_PAYMENTS, doc)

    # A confirmed payment must not become an orphan when an open folio exists.
    # The folio guard is atomic, so post it before creating the ledger entry:
    # if two tellers pay the last balance concurrently, only one payment can
    # remain confirmed. Payments created before check-in are intentionally
    # allowed to remain confirmed without a folio; create_folio() reconciles
    # them later by their stable payment reference.
    if status == "confirmed":
        open_folio_exists = db.guest_folios.find_one(
            {"booking_id": doc["booking_id"], "status": "open"},
            {"_id": 1},
        ) is not None
        folio = None
        try:
            from src.app.modules.billing.service.folio import post_to_folio
            folio = post_to_folio(
                doc["booking_id"],
                posting_type="payment",
                category=doc.get("method", "Payment").title(),
                concept=f"Pago {doc.get('reference', '')}",
                amount=float(doc.get("amount", 0) or 0),
                reference_id=doc.get("reference", ""),
                reference_type="payment",
                posted_at=doc.get("paid_at"),
            )
        except Exception:
            logger.exception("Failed to post payment %s to guest folio", doc.get("reference", ""))

        if open_folio_exists and folio is None:
            # The payment document and its fact mirror already exist. Mark the
            # attempt failed through the same dual-write path instead of
            # silently returning a confirmed payment with no folio evidence.
            failure_time = _now()
            _update_both(
                PAYMENTS,
                FACT_PAYMENTS,
                doc["_id"],
                {"$set": {
                    "status": "failed",
                    "failure_reason": "folio_balance_or_posting_conflict",
                    "updated_at": failure_time,
                }},
            )
            doc["status"] = "failed"
            doc["failure_reason"] = "folio_balance_or_posting_conflict"
            _emit_payment_domain_event(doc)
            return _enrich_payment(doc)

        try:
            from src.app.modules.expenses.service.ledger_hooks import generate_ledger_from_payment
            ledger_entries = generate_ledger_from_payment(doc)
            if ledger_entries != 2:
                raise RuntimeError(
                    f"payment ledger incomplete: expected 2 entries, got {ledger_entries}"
                )
        except Exception:
            # Keep the payment retryable rather than exposing a confirmed
            # payment with no GL evidence. The folio posting is compensated by
            # a durable reversal event so totals also return to their prior
            # state.
            logger.exception("Failed to generate ledger entries for payment %s", doc.get("reference", ""))
            try:
                from src.app.modules.billing.service.folio import post_to_folio
                post_to_folio(
                    doc["booking_id"],
                    posting_type="refund",
                    category="Payment rollback",
                    concept=f"Rollback de pago {doc.get('reference', '')}",
                    amount=float(doc.get("amount", 0) or 0),
                    reference_id=f"ROLLBACK-{doc.get('reference', '')}",
                    reference_type="payment_rollback",
                )
            except Exception:
                logger.exception("Failed to compensate folio for payment %s", doc.get("reference", ""))
            failure_time = _now()
            _update_both(
                PAYMENTS,
                FACT_PAYMENTS,
                doc["_id"],
                {"$set": {
                    "status": "failed",
                    "failure_reason": "ledger_posting_failed",
                    "updated_at": failure_time,
                }},
            )
            doc["status"] = "failed"
            doc["failure_reason"] = "ledger_posting_failed"
            _emit_payment_domain_event(doc)
            return _enrich_payment(doc)

        # The payment was inserted as confirmed and all required side effects
        # succeeded. Mirror the timestamp without changing its state.
        confirmed_time = _now()
        _update_both(
            PAYMENTS,
            FACT_PAYMENTS,
            doc["_id"],
            {"$set": {"status": "confirmed", "updated_at": confirmed_time}},
        )
        doc["status"] = "confirmed"

    if invoice_id and status == "confirmed" and doc.get("status") == "confirmed":
        confirmed_total = round(sum(
            float(row.get("amount", 0) or 0)
            for row in db[PAYMENTS].find({"invoice_id": invoice_id, "status": "confirmed"}, {"amount": 1})
        ), 2)
        invoice = db[INVOICES].find_one({"_id": invoice_id}, {"total": 1})
        invoice_total = round(float((invoice or {}).get("total", 0) or 0), 2)
        next_status = "paid" if confirmed_total >= invoice_total - 0.01 else "partially_paid"
        upd = {"$set": {"status": next_status, "paid_at": _now() if next_status == "paid" else None,
                         "total_paid_amount": confirmed_total}}
        _update_both(INVOICES, FACT_INVOICES, invoice_id, upd)

    _emit_payment_domain_event(doc)
    doc["_id"] = doc.pop("_id", None)
    return _enrich_payment(doc)


def list_payments(
    booking_id: str | None = None,
    prop_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    sin_turno: bool = False,
    shift_id: str | None = None,
    employee: str | None = None,
) -> dict:
    db = get_database()
    query: dict = {}
    if prop_id:
        query["prop_id"] = prop_id
    if booking_id:
        booking = _find_booking(booking_id)
        booking_str_id = booking.get("booking_id") if booking else booking_id
        query["booking_id"] = booking_str_id
    if sin_turno:
        # Legacy payments without shift attribution: `shift_id` missing or null.
        query["shift_id"] = None
    if shift_id:
        # Audit filter: exact shift that collected the payment.
        try:
            query["shift_id"] = ObjectId(shift_id)
        except Exception:
            query["shift_id"] = shift_id
    if employee and employee.strip():
        # Audit filter: cashier that handled the money — matches the shift's
        # employee label OR the IAM opener (case-insensitive contains).
        rx = {"$regex": re.escape(employee.strip()), "$options": "i"}
        query["$or"] = [{"shift_employee": rx}, {"shift_opened_by": rx}]
    total = db[PAYMENTS].count_documents(query)
    cursor = (
        db[PAYMENTS]
        .find(query)
        .sort("paid_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_payment(doc) for doc in cursor]
    # Badge for the payments list: how many legacy (unattributed) payments the
    # hotel still has pending shift-linking. Scoped to the same prop (or all
    # hotels when no prop filter), matching exactly what ``sin_turno`` shows.
    legacy_query: dict = {"shift_id": None}
    if prop_id:
        legacy_query["prop_id"] = prop_id
    legacy_pending_count = db[PAYMENTS].count_documents(legacy_query)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
        "legacy_pending_count": legacy_pending_count,
    }


def link_payment_to_shift(
    payment_id: str,
    shift_id: str,
    *,
    changed_by: str = "system",
) -> dict:
    """Link a legacy payment (without attribution) to the responsible shift.

    Stamps the shift FK plus the denormalized employee/opener attribution on
    the payment and its fact mirror, so cash-control reconciliation and the
    payments list show who handled the collection.

    Raises ``ValueError`` with a machine-readable code on conflicts:
    - ``payment_not_found`` / ``shift_not_found``
    - ``payment_already_linked`` (the payment already carries a shift)
    - ``shift_prop_mismatch`` (shift belongs to another property)
    """
    db = get_database()
    try:
        pay_id = ObjectId(payment_id)
    except Exception:
        raise ValueError("payment_not_found") from None
    payment = db[PAYMENTS].find_one({"_id": pay_id})
    if not payment:
        raise ValueError("payment_not_found")
    if payment.get("shift_id"):
        raise ValueError("payment_already_linked")

    try:
        shift_oid = ObjectId(shift_id)
    except Exception:
        raise ValueError("shift_not_found") from None
    shift = db.reception_shifts.find_one({"_id": shift_oid})
    if not shift:
        raise ValueError("shift_not_found")
    if int(shift.get("prop_id", 0) or 0) != int(payment.get("prop_id", 0) or 0):
        raise ValueError("shift_prop_mismatch")

    update: dict = {"shift_id": shift_oid, "updated_at": _now()}
    attr = _shift_attribution(str(shift_oid))
    if attr:
        update.update(attr)
    update["shift_linked_by"] = changed_by
    update["shift_linked_at"] = _now()

    _update_both(PAYMENTS, FACT_PAYMENTS, pay_id, {"$set": update})
    refreshed = db[PAYMENTS].find_one({"_id": pay_id})
    if refreshed:
        db[FACT_PAYMENTS].replace_one({"_id": pay_id}, dict(refreshed), upsert=True)
    return _enrich_payment(refreshed)


def get_payment(payment_id: str) -> dict | None:
    db = get_database()
    try:
        from bson.errors import InvalidId
        doc = db[PAYMENTS].find_one({"_id": ObjectId(payment_id)})
    except (InvalidId, Exception):
        return None
    return _enrich_payment(doc) if doc else None


def classify_failed_payment_informational(
    payment_id: str,
    *,
    changed_by: str = "historical_reconciliation",
) -> dict | None:
    """Mark a failed payment without invoice as informational only.

    The failed gateway attempt remains in payment facts and never creates an
    invoice, folio posting, or ledger movement. The explicit marker keeps
    reconciliation and UI behavior stable on retries.
    """
    db = get_database()
    try:
        pay_id = ObjectId(payment_id)
    except Exception:
        return None
    payment = db[PAYMENTS].find_one({"_id": pay_id})
    if not payment or str(payment.get("status", "")).lower() not in {"failed", "rejected", "declined", "error"}:
        return None
    if payment.get("invoice_id") not in (None, ""):
        return None
    now = _now()
    update = {
        "reconciliation_status": "informational",
        "reconciliation_reason": "failed_payment_without_invoice_no_balance_effect",
        "reconciliation_changed_by": changed_by,
        "reconciliation_changed_at": now,
        "updated_at": now,
    }
    _update_both(PAYMENTS, FACT_PAYMENTS, pay_id, {"$set": update})
    refreshed_payment = db[PAYMENTS].find_one({"_id": pay_id})
    if refreshed_payment:
        db[FACT_PAYMENTS].replace_one({"_id": pay_id}, dict(refreshed_payment), upsert=True)
    db.payment_reconciliation_events.update_one(
        {"payment_id": str(pay_id), "event": "classified_informational"},
        {"$setOnInsert": {
            "payment_id": str(pay_id),
            "prop_id": payment.get("prop_id", 0),
            "event": "classified_informational",
            "reason": update["reconciliation_reason"],
            "changed_by": changed_by,
            "changed_at": now,
        }},
        upsert=True,
    )
    refreshed = db[PAYMENTS].find_one({"_id": pay_id})
    return _enrich_payment(refreshed) if refreshed else None


def refund_payment(
    payment_id: str,
    *,
    refund_id: str | None = None,
    refund_reason: str | None = None,
    changed_by: str | None = None,
    shift_id: str | None = None,
) -> dict | None:
    """Refund a confirmed payment, persisting the refund history on the doc.

    ``refund_reason`` (motivo/nota del reembolso) y ``changed_by`` (quién lo
    ejecutó) quedan guardados en Mongo sobre el pago y su espejo de hechos,
    para que el historial del reembolso sea auditable. Ambos son opcionales:
    una llamada sin ellos conserva el comportamiento legacy (sin campos extra).

    ``shift_id`` (opcional) estampa el turno del cajero responsable del
    reembolso (``refund_shift_id`` + atribución) sobre el pago y su espejo.
    """
    db = get_database()
    try:
        from bson.errors import InvalidId
        pay_id = ObjectId(payment_id)
    except (InvalidId, Exception):
        return None

    pay = db[PAYMENTS].find_one({"_id": pay_id})
    if not pay:
        return None

    current_status = pay.get("status", "")
    requested_refund_id = str(refund_id or "").strip() or None
    normalized_reason = str(refund_reason or "").strip() or None
    if current_status == "refunded":
        # An explicit refund id makes a retry safe and observable. Legacy calls
        # without one retain the old duplicate-refund response so clients can
        # migrate deliberately instead of silently changing their contract.
        if requested_refund_id and pay.get("refund_id") == requested_refund_id:
            return _enrich_payment(pay)
        return None
    try:
        payment_sm.validate_transition(current_status, "refunded")
    except ValueError:
        return None

    # Refund side effects are compensating, idempotent events. They must finish
    # before the payment is marked refunded; otherwise a ledger/folio outage
    # makes the state terminal and prevents a retry from repairing it.
    payment_ref = str(pay.get("reference") or pay_id)
    event_id = requested_refund_id or payment_ref
    booking_id = pay.get("booking_id") or ""
    folio_exists = db.guest_folios.find_one(
        {"booking_id": booking_id}, {"_id": 1}
    ) is not None
    try:
        from src.app.modules.billing.service.folio import post_to_folio
        folio_result = post_to_folio(
            booking_id,
            posting_type="refund",
            category="Refund",
            concept=f"Reembolso {payment_ref}",
            amount=float(pay.get("amount", 0) or 0),
            reference_id=event_id,
            reference_type="payment_refund",
        )
        if folio_exists and folio_result is None:
            raise RuntimeError("guest folio is unavailable for refund reversal")

        from src.app.modules.expenses.service.ledger_hooks import post_journal_entry
        post_journal_entry(
            amount=float(pay.get("amount", 0) or 0),
            dr_account_code="1030",
            dr_account_name="Cuentas por Cobrar Huéspedes",
            cr_account_code="1010",
            cr_account_name="Caja / Bancos",
            description=f"Reembolso {event_id}",
            prop_id=int(pay.get("prop_id", 0) or 0),
            source="payment_refund",
            source_id=event_id,
            booking_id=booking_id,
        )
        # The ledger event is retained for compatibility, but every refund now
        # also has a formal receipt/credit note and a denormalized fact mirror.
        from src.app.modules.billing.service.lifecycle.refunds import ensure_refund_document_for_payment
        refund_document = ensure_refund_document_for_payment(
            str(pay_id),
            changed_by="billing_refund",
        )
        if refund_document is None:
            raise RuntimeError("refund document could not be issued")
    except Exception:
        logger.exception("Failed to complete refund reversal for %s; payment remains retryable", payment_ref)
        return None

    now = _now()
    refund_set: dict = {"status": "refunded", "refund_id": event_id, "refunded_at": now, "updated_at": now}
    # Historial auditable del reembolso: motivo/nota y quién lo ejecutó. Solo se
    # escriben cuando se proveen, para no contaminar el doc legacy.
    if normalized_reason:
        refund_set["refund_reason"] = normalized_reason
    if changed_by:
        refund_set["refunded_by"] = changed_by
    # Turno responsable del reembolso (opcional): estampa el FK + atribución.
    if shift_id:
        refund_set["refund_shift_id"] = ObjectId(shift_id) if _valid_object_id(shift_id) else shift_id
        attr = _shift_attribution(shift_id)
        if attr:
            for key in ("shift_employee", "shift_opened_by", "shift_opened_by_id", "shift_type"):
                if attr.get(key) is not None:
                    refund_set[f"refund_{key}"] = attr[key]
    updated = db[PAYMENTS].find_one_and_update(
        {"_id": pay_id, "status": current_status},
        {"$set": refund_set},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        return None
    _update_both(
        PAYMENTS,
        FACT_PAYMENTS,
        pay_id,
        {"$set": refund_set},
    )

    if updated.get("invoice_id"):
        inv_id = updated["invoice_id"]
        _update_both(
            INVOICES,
            FACT_INVOICES,
            inv_id,
            {"$set": {"status": "refunded", "updated_at": now}},
        )
    _emit_payment_domain_event(updated)
    return _enrich_payment(updated)
