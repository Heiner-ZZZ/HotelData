"""Invoice CRUD operations."""

from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument

from src.database.connection import get_database

logger = logging.getLogger(__name__)
from src.app.core.resolvers import resolve_hotel_id


def _booking_total_without_additional_charges(
    db, booking_id: str, prior_additional_total: float = 0.0,
) -> float:
    """Preserve non-additional booking charges during charge reconciliation.

    Some legacy bookings keep service/amenity totals only in ``total_charges``
    and have no corresponding ``line_items``. Prefer the explicit line-item
    projection when it is present, but always retain the current aggregate
    minus the prior additional-charge projection so reconciliation cannot erase
    an unrelated operational charge.
    """
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id}, {"line_items": 1, "total_charges": 1},
    ) or {}
    line_items = booking.get("line_items") or []
    line_total = round(sum(
        float(item.get("total", 0) or 0)
        for item in line_items
        if isinstance(item, dict) and item.get("type") != "additional_charge"
    ), 2)
    aggregate_without_prior = round(
        max(float(booking.get("total_charges", 0) or 0) - float(prior_additional_total or 0), 0),
        2,
    )
    return max(line_total, aggregate_without_prior)
from src.app.core.state_machine import invoice_sm
from src.app.modules.billing.schemas import InvoiceCreate
from src.app.modules.billing.service.lifecycle._helpers import (
    _enrich_invoice,
    _enrich_payment,
    _find_booking,
    _generate_invoice_number,
    _now,
    _update_both,
    _write_both,
    FACT_INVOICES,
    FACT_PAYMENTS,
    INVOICES,
    PAYMENTS,
)


def _record_earnings(booking: dict, invoice_total: float) -> None:
    """Calculate and record platform commission earnings."""
    db = get_database()
    prop_id = booking.get("prop_id", 0)
    booking_id = booking.get("booking_id", "")

    commission_cfg = db.commission_rates.find_one({"prop_id": prop_id}, {"commission_pct": 1, "_id": 0})
    if commission_cfg:
        commission_pct = commission_cfg.get("commission_pct", 5.0)
    else:
        sys_config = db.system_config.find_one({"_id": "global"}, {"default_commission_pct": 1, "_id": 0})
        commission_pct = sys_config.get("default_commission_pct", 5.0) if sys_config else 5.0

    commission_amount = round(invoice_total * commission_pct / 100, 2)

    from src.app.modules.partner.services.hotel_products import record_platform_earnings
    record_platform_earnings(
        booking_id=booking_id,
        prop_id=prop_id,
        commission_pct=commission_pct,
        booking_total=invoice_total,
        commission_amount=commission_amount,
    )


def generate_invoice_for_booking(
    booking_id: str, total_price: float | None = None,
    currency: str = "USD", notes: str = "",
) -> dict | None:
    """Auto-generate an invoice for a booking when confirmed."""
    booking = _find_booking(booking_id)
    if not booking:
        return None

    price = total_price if total_price is not None else booking.get("total_price")
    if price is None:
        price = 0.0
    price = float(price)
    subtotal = round(price / 1.16, 2)
    taxes = round(price - subtotal, 2)

    payload = InvoiceCreate(
        booking_id=booking.get("booking_id") or booking_id,
        subtotal=subtotal,
        taxes=taxes,
        notes=notes or f"Factura generada automáticamente por confirmación de reserva {booking.get('booking_id', '')}",
    )
    return create_invoice(payload)


def create_invoice(
    payload: InvoiceCreate,
    *,
    shift_id: str | None = None,
    shift_attribution: dict | None = None,
) -> dict | None:
    booking = _find_booking(payload.booking_id)
    if not booking:
        return None

    line_items = booking.get("line_items", [])
    extras_total = sum(float(item.get("total", 0)) for item in line_items)
    room_subtotal = round(payload.subtotal, 2)
    total_subtotal = round(room_subtotal + extras_total, 2)
    total = round(total_subtotal + payload.taxes, 2)

    # Guard: nunca emitir facturas en $0 o negativas, ni siquiera cuando la
    # reserva tiene line_items (cargos que se anulan entre sí, descuentos o
    # créditos que cancelan el subtotal). Una factura sin valor no tiene valor
    # fiscal y contamina los KPIs tácticos (F1.4/F1.5) y las estadísticas de
    # facturación.
    if total <= 0:
        logger.warning(
            "Creación de factura rechazada para %s: total $%.2f sin valor (subtotal+extras+taxes)",
            payload.booking_id,
            total,
        )
        return None

    doc = {
        "booking_id": booking.get("booking_id") or payload.booking_id,
        "prop_id": booking.get("prop_id", 0),
        "hotel_id": resolve_hotel_id(booking.get("prop_id", 0)),
        "invoice_number": _generate_invoice_number(),
        "subtotal": total_subtotal,
        "room_subtotal": room_subtotal,
        "extras_total": extras_total,
        "line_items": line_items,
        "taxes": round(payload.taxes, 2),
        "total": total,
        "status": "issued",
        "notes": payload.notes or None,
        "issued_at": _now(),
        "paid_at": None,
    }
    # Cashier attribution: the shift that issued the fiscal document and the
    # employee/opener, denormalized so reports don't need the join (parity
    # with payments and folio postings). Null for legacy/service writes.
    if shift_id:
        try:
            doc["shift_id"] = ObjectId(shift_id)
        except Exception:
            doc["shift_id"] = shift_id
        if shift_attribution:
            for key in ("shift_employee", "shift_opened_by", "shift_opened_by_id", "shift_type"):
                if shift_attribution.get(key):
                    doc[key] = shift_attribution[key]
    else:
        doc["shift_id"] = None
    _write_both(INVOICES, FACT_INVOICES, doc)

    # Reconcile the invoice's complete accounting projection before exposing it.
    # The helper is idempotent and marks a retryable failure instead of leaving
    # an apparently valid invoice with an unknown GL state.
    try:
        reconciled_invoice = reconcile_positive_invoice_accounting(
            str(doc["_id"]),
            changed_by="billing_invoice_creation",
        )
        if reconciled_invoice:
            doc.update({
                key: reconciled_invoice[key]
                for key in (
                    "accounting_status",
                    "ledger_posting_status",
                    "ledger_posting_error",
                    "ledger_references",
                    "accounting_reconciled_at",
                    "accounting_reconciled_by",
                )
                if key in reconciled_invoice
            })
    except Exception:
        logger.exception("Failed to reconcile ledger entries for invoice %s", doc.get("invoice_number", ""))
        failure = {
            "accounting_status": "failed",
            "ledger_posting_status": "failed",
            "ledger_posting_error": "No se pudo conciliar el asiento de la factura",
        }
        db = get_database()
        db[INVOICES].update_one({"_id": doc["_id"]}, {"$set": failure})
        db[FACT_INVOICES].update_one({"_id": doc["_id"]}, {"$set": failure})
        doc.update(failure)

    try:
        _record_earnings(booking, total)
    except Exception:
        logger.exception("Failed to record earnings for booking %s", payload.booking_id)

    try:
        from src.app.modules.financial_reconciliation.domain_events import append_domain_event
        append_domain_event(
            prop_id=int(doc.get("prop_id", 0) or 0),
            event_type="guest_ar.invoice.issued",
            aggregate_type="guest_ar",
            aggregate_id=str(doc.get("invoice_number", "")),
            idempotency_key=f"live:invoice:issued:{doc.get('invoice_number', '')}",
            payload={"booking_id": doc.get("booking_id"), "total": doc.get("total", 0), "status": doc.get("status")},
            source_collection=INVOICES,
            source_id=str(doc.get("invoice_number", "")),
        )
    except Exception:
        logger.exception("Failed to emit domain event for invoice %s", doc.get("invoice_number", ""))

    doc["_id"] = doc.pop("_id", None)
    return _enrich_invoice(doc)


def reconstruct_historical_invoice_for_folio(
    booking_id: str,
    *,
    changed_by: str = "historical_reconciliation",
    approval_reference: str,
    actor_user_id: ObjectId | str | None = None,
) -> dict | None:
    """Create/reuse an internal AR invoice for a settled historical folio.

    This is documentary, not a fiscal invoice. It links the existing folio and
    confirmed payment, then posts only folio components that have no balanced
    ledger pair yet. Existing ``folio_posting`` revenue is never duplicated.
    """
    db = get_database()
    actor_oid = None
    if actor_user_id:
        try:
            actor_oid = actor_user_id if isinstance(actor_user_id, ObjectId) else ObjectId(str(actor_user_id))
        except Exception as exc:
            raise ValueError("actor_user_id inválido") from exc
    folio = db.guest_folios.find_one({"booking_id": booking_id, "status": "settled", "total_due": {"$lte": 0.005}})
    if not folio:
        return None
    invoice_postings = [
        posting for posting in (folio.get("postings") or [])
        if posting.get("type") not in {"payment", "refund", "discount"}
    ]
    total_room = round(float(folio.get("total_room", 0) or 0), 2)
    posting_total = round(sum(float(posting.get("amount", 0) or 0) for posting in invoice_postings), 2)
    total = posting_total if invoice_postings else round(total_room + float(folio.get("total_charges", 0) or 0), 2)
    total_charges = round(total - total_room, 2)
    if total <= 0:
        raise ValueError("El folio histórico no tiene un total positivo reconstruible")

    # A booking may contain an older confirmed online payment that is not
    # applied to this folio. Select the payment represented by the folio's
    # payment posting first; falling back to an exact-total payment keeps old
    # settled folios compatible without silently assigning an unrelated
    # confirmed payment to the reconstructed invoice.
    payment_refs = {
        str(posting.get("reference_id"))
        for posting in (folio.get("postings") or [])
        if posting.get("type") == "payment" and posting.get("reference_id")
    }
    payment_query = {
        "booking_id": booking_id,
        "status": "confirmed",
        "amount": {"$gt": 0},
    }
    applied_payments: list[dict] = []
    if payment_refs:
        applied_payments = list(db[PAYMENTS].find(
            {**payment_query, "reference": {"$in": sorted(payment_refs)}},
        ).sort("paid_at", -1))
    if not applied_payments:
        exact_payments = list(db[PAYMENTS].find(payment_query).sort("paid_at", -1))
        exact_payment = next(
            (
                candidate for candidate in exact_payments
                if abs(round(float(candidate.get("amount", 0) or 0), 2) - total) <= 0.01
            ),
            None,
        )
        if exact_payment:
            applied_payments = [exact_payment]
    if not applied_payments:
        raise ValueError("El folio histórico no tiene un pago confirmado aplicado por el total")
    payment = applied_payments[0]
    payment_amount = round(sum(float(row.get("amount", 0) or 0) for row in applied_payments), 2)
    if abs(payment_amount - total) > 0.01:
        raise ValueError("Los pagos confirmados aplicados no cubren exactamente el total histórico del folio")
    if not approval_reference.strip():
        raise ValueError("approval_reference es obligatorio para una factura histórica")

    invoice_number = f"HINV-{folio.get('folio_number', booking_id)}"
    invoice = db[INVOICES].find_one({
        "booking_id": booking_id,
        "source": "historical_reconstruction",
        "folio_id": folio["_id"],
    })
    legacy_invoice = db[INVOICES].find_one({
        "booking_id": booking_id,
        "source": {"$ne": "historical_reconstruction"},
        "status": {"$in": ["cancelled", "refunded"]},
    }, sort=[("issued_at", -1)])
    effective_at = payment.get("paid_at") or folio.get("settled_at") or _now()
    if invoice is None:
        line_items = [
            {
                "item_id": str(posting.get("posting_id", "")),
                "type": posting.get("reference_type") or posting.get("type", "charge"),
                "name": posting.get("concept", ""),
                "category": posting.get("category", "Otros"),
                "quantity": int(posting.get("quantity", 1) or 1),
                "unit_price": round(float(posting.get("unit_price", posting.get("amount", 0)) or 0), 2),
                "total": round(float(posting.get("amount", 0) or 0), 2),
                "reference_id": posting.get("reference_id", ""),
                "reference_type": posting.get("reference_type", ""),
                "posted_at": posting.get("posted_at"),
            }
            for posting in invoice_postings
        ]
        invoice_doc = {
            "booking_id": booking_id,
            "prop_id": int(folio.get("prop_id", 0) or 0),
            "hotel_id": folio.get("hotel_id") or resolve_hotel_id(folio.get("prop_id", 0)),
            "folio_id": folio["_id"],
            "folio_number": folio.get("folio_number", ""),
            "invoice_number": invoice_number,
            "supersedes_invoice_id": legacy_invoice["_id"] if legacy_invoice else None,
            "subtotal": total,
            "room_subtotal": total_room,
            "extras_total": total_charges,
            "taxes": 0.0,
            "total": total,
            "total_paid_amount": payment_amount,
            "line_items": line_items,
            "status": "paid",
            "source": "historical_reconstruction",
            "is_fiscal_document": False,
            "reconstructed_by_user_id": actor_oid,
            "reconstructed_by_username": changed_by,
            "historical_reconstruction": {
                "approval_reference": approval_reference.strip(),
                "changed_by": changed_by,
                "actor_user_id": actor_oid,
                "effective_at": effective_at,
                "reason": "Documento interno Guest AR reconstruido desde folio liquidado.",
            },
            "accounting_status": "pending",
            "issued_at": effective_at,
            "paid_at": payment.get("paid_at") or effective_at,
            "notes": "Documento interno histórico; no sustituye una factura fiscal.",
        }
        _write_both(INVOICES, FACT_INVOICES, invoice_doc)
        invoice = db[INVOICES].find_one({"_id": invoice_doc["_id"]})
    invoice_id = invoice["_id"]
    now = _now()
    if actor_oid:
        actor_update = {
            "reconstructed_by_user_id": actor_oid,
            "reconstructed_by_username": changed_by,
            "historical_reconstruction.actor_user_id": actor_oid,
            "historical_reconstruction.changed_by": changed_by,
            "updated_at": now,
        }
        db[INVOICES].update_one({"_id": invoice_id}, {"$set": actor_update})
        db[FACT_INVOICES].update_one({"_id": invoice_id}, {"$set": actor_update})
    if legacy_invoice and legacy_invoice["_id"] != invoice_id:
        # Preserve the cancelled/refunded document, but make its replacement
        # explicit so canonical readers never treat both as active truth.
        legacy_update = {
            "$set": {
                "is_deleted": True,
                "deleted_at": now,
                "deleted_by": changed_by,
                "deleted_by_user_id": actor_oid,
                "deletion_reason": "superseded_by_historical_reconstruction",
                "replaced_by_invoice_id": invoice_id,
                "replacement_status": "superseded",
                "updated_at": now,
            }
        }
        db[INVOICES].update_one({"_id": legacy_invoice["_id"]}, legacy_update)
        updated_legacy = db[INVOICES].find_one({"_id": legacy_invoice["_id"]})
        if updated_legacy:
            db[FACT_INVOICES].replace_one({"_id": legacy_invoice["_id"]}, dict(updated_legacy), upsert=True)
        db[INVOICES].update_one({"_id": invoice_id}, {"$set": {"supersedes_invoice_id": legacy_invoice["_id"], "updated_at": now}})
        db[FACT_INVOICES].update_one({"_id": invoice_id}, {"$set": {"supersedes_invoice_id": legacy_invoice["_id"], "updated_at": now}})

    for applied_payment in applied_payments:
        payment_update = {
            "invoice_id": invoice_id,
            "folio_id": folio["_id"],
            "folio_number": folio.get("folio_number", ""),
        }
        if applied_payment.get("invoice_id") != invoice_id or applied_payment.get("folio_id") != folio["_id"]:
            _update_both(PAYMENTS, FACT_PAYMENTS, applied_payment["_id"], {"$set": payment_update})
        updated_payment = db[PAYMENTS].find_one({"_id": applied_payment["_id"]})
        if updated_payment:
            # Legacy historical payments may predate their fact mirror; make
            # the invoice + folio links complete in both operational and fact
            # stores, even when the invoice link was already present.
            db[FACT_PAYMENTS].replace_one(
                {"_id": applied_payment["_id"]},
                dict(updated_payment),
                upsert=True,
            )

    if folio.get("invoice_id") != invoice_id or folio.get("settlement_invoice_id") != invoice_id:
        db.guest_folios.update_one({"_id": folio["_id"]}, {"$set": {
            "invoice_id": invoice_id,
            "settlement_invoice_id": invoice_id,
            "updated_at": _now(),
        }})

    # Settlement events are written before historical invoices are rebuilt.
    # Complete that second half of the trace here and refresh the denormalized
    # fact mirror so every reader sees the same payment → folio → invoice link.
    settlement_trace = None
    settlement_traces: list[dict[str, Any]] = []
    for settlement_event in db.folio_settlement_events.find({"folio_id": folio["_id"]}):
        event_update = {"invoice_id": invoice_id, "folio_id": folio["_id"]}
        if not settlement_event.get("shift_id") and settlement_event.get("payment_id"):
            linked_payment = db[PAYMENTS].find_one({"_id": settlement_event["payment_id"]}, {"shift_id": 1})
            if linked_payment and linked_payment.get("shift_id"):
                event_update["shift_id"] = linked_payment["shift_id"]
        db.folio_settlement_events.update_one(
            {"_id": settlement_event["_id"]}, {"$set": event_update},
        )
        refreshed_event = db.folio_settlement_events.find_one({"_id": settlement_event["_id"]})
        if refreshed_event:
            db.fact_folio_settlement_events.replace_one(
                {"_id": settlement_event["_id"]}, dict(refreshed_event), upsert=True,
            )
            settlement_trace = refreshed_event
            settlement_traces.append(refreshed_event)

    if settlement_trace:
        settlement_shift_ids = [
            event["shift_id"] for event in settlement_traces if event.get("shift_id")
        ]
        db.guest_folios.update_one({"_id": folio["_id"]}, {"$set": {
            "settlement_event_id": settlement_trace["_id"],
            "settlement_payment_id": settlement_trace.get("payment_id"),
            "settlement_shift_id": settlement_trace.get("shift_id"),
            "settlement_invoice_id": invoice_id,
            "settlement_event_ids": [event["_id"] for event in settlement_traces],
            "settlement_payment_ids": [event.get("payment_id") for event in settlement_traces if event.get("payment_id")],
            "settlement_shift_ids": settlement_shift_ids,
            "updated_at": _now(),
        }})

    missing_room = 0.0
    missing_services = 0.0
    missing_transfers: list[tuple[str, str, float]] = []
    for posting in (folio.get("postings") or []):
        if posting.get("type") not in {"room", "charge", "adjustment"}:
            continue
        if posting.get("type") == "adjustment" and posting.get("reference_type") in {"folio_transfer_out", "folio_transfer_in"}:
            transfer_reference = str(posting.get("reference_id") or posting.get("posting_id") or "")
            transfer_rows = list(db["ledger_transactions"].find({"source": "folio_transfer", "source_id": transfer_reference}, {"debit": 1, "credit": 1}))
            transfer_balanced = len(transfer_rows) == 2 and round(sum(float(row.get("debit", 0) or 0) for row in transfer_rows), 2) == round(sum(float(row.get("credit", 0) or 0) for row in transfer_rows), 2)
            if not transfer_balanced:
                missing_transfers.append((str(posting.get("reference_type")), transfer_reference, abs(round(float(posting.get("amount", 0) or 0), 2))))
            continue
        posting_id = str(posting.get("posting_id", ""))
        rows = list(db["ledger_transactions"].find({"source": "folio_posting", "source_id": posting_id}, {"debit": 1, "credit": 1}))
        balanced = len(rows) == 2 and round(sum(float(row.get("debit", 0) or 0) for row in rows), 2) == round(sum(float(row.get("credit", 0) or 0) for row in rows), 2)
        if balanced:
            continue
        amount = round(float(posting.get("amount", 0) or 0), 2)
        if posting.get("type") == "room":
            missing_room += amount
        elif posting.get("type") == "charge" and amount > 0:
            missing_services += amount

    ledger_references: list[str] = []
    from src.app.modules.expenses.service.ledger_hooks import post_journal_entry
    if missing_room > 0:
        ledger_references.append(post_journal_entry(
            amount=round(missing_room, 2),
            dr_account_code="1030",
            dr_account_name="Cuentas por Cobrar Huéspedes",
            cr_account_code="4010",
            cr_account_name="Ingresos por Alojamiento",
            description=f"Reconstrucción histórica de alojamiento — {invoice_number}",
            prop_id=int(folio.get("prop_id", 0) or 0),
            source="historical_invoice",
            source_id=invoice_number,
            booking_id=booking_id,
            tx_date=effective_at,
        ))
    if missing_services > 0:
        ledger_references.append(post_journal_entry(
            amount=round(missing_services, 2),
            dr_account_code="1030",
            dr_account_name="Cuentas por Cobrar Huéspedes",
            cr_account_code="4030",
            cr_account_name="Ingresos por Servicios",
            description=f"Reconstrucción histórica de servicios — {invoice_number}",
            prop_id=int(folio.get("prop_id", 0) or 0),
            source="historical_invoice",
            source_id=invoice_number + ":services",
            booking_id=booking_id,
            tx_date=effective_at,
        ))
    for transfer_type, transfer_reference, transfer_amount in missing_transfers:
        if transfer_amount <= 0:
            continue
        if transfer_type == "folio_transfer_out":
            debit_code, debit_name = "1090", "Transferencias internas entre folios"
            credit_code, credit_name = "1030", "Cuentas por Cobrar Huéspedes"
        else:
            debit_code, debit_name = "1030", "Cuentas por Cobrar Huéspedes"
            credit_code, credit_name = "1090", "Transferencias internas entre folios"
        ledger_references.append(post_journal_entry(
            amount=transfer_amount,
            dr_account_code=debit_code,
            dr_account_name=debit_name,
            cr_account_code=credit_code,
            cr_account_name=credit_name,
            description=f"Reconstrucción de transferencia entre folios — {transfer_reference}",
            prop_id=int(folio.get("prop_id", 0) or 0),
            source="folio_transfer",
            source_id=transfer_reference,
            booking_id=booking_id,
            tx_date=effective_at,
        ))

    accounting_status = "posted"
    db[INVOICES].update_one({"_id": invoice_id}, {"$set": {
        "status": "paid",
        "total_paid_amount": payment_amount,
        "accounting_status": accounting_status,
        "ledger_posting_status": accounting_status,
        "ledger_references": ledger_references,
        "updated_at": _now(),
    }})
    db[FACT_INVOICES].update_one({"_id": invoice_id}, {"$set": {
        "status": "paid",
        "total_paid_amount": payment_amount,
        "accounting_status": accounting_status,
        "ledger_posting_status": accounting_status,
        "ledger_references": ledger_references,
        "updated_at": _now(),
    }})

    try:
        from src.app.modules.financial_reconciliation.domain_events import append_domain_event
        append_domain_event(
            prop_id=int(folio.get("prop_id", 0) or 0),
            event_type="guest_ar.invoice.historical_reconstructed",
            aggregate_type="guest_ar",
            aggregate_id=str(invoice_id),
            idempotency_key=f"historical-invoice:{invoice_number}",
            payload={"booking_id": booking_id, "folio_id": str(folio["_id"]), "invoice_number": invoice_number, "total": total, "ledger_references": ledger_references, "actor_user_id": str(actor_oid) if actor_oid else None, "actor_username": changed_by},
            source_collection=INVOICES,
            source_id=str(invoice_id),
            actor_id=str(actor_oid) if actor_oid else changed_by,
        )
    except Exception:
        logger.exception("Failed to emit historical invoice domain event %s", invoice_number)

    if not db.audit_log.find_one({"entity_type": "historical_invoice", "entity_id": booking_id, "action": "reconstruct", "metadata.invoice_number": invoice_number}):
        from src.app.modules.partner.services.audit import register_action
        register_action(
            prop_id=int(folio.get("prop_id", 0) or 0),
            entity_type="historical_invoice",
            entity_id=booking_id,
            action="reconstruct",
            summary=f"Reconstrucción de documento AR histórico {invoice_number}",
            changed_by=changed_by,
            metadata={"invoice_number": invoice_number, "folio_number": folio.get("folio_number"), "approval_reference": approval_reference.strip(), "ledger_references": ledger_references, "actor_user_id": str(actor_oid) if actor_oid else None},
        )

    refreshed = db[INVOICES].find_one({"_id": invoice_id})
    return _enrich_invoice(refreshed) if refreshed else None


def list_invoices(
    booking_id: str | None = None,
    prop_id: int | None = None,
    status: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 20,
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
    if status:
        query["status"] = status
    if date_from or date_to:
        issued_q: dict = {}
        if date_from:
            issued_q["$gte"] = date_from
        if date_to:
            issued_q["$lte"] = date_to + "T23:59:59"
        query["issued_at"] = issued_q
    if shift_id:
        # Audit filter: exact shift that issued the fiscal document.
        try:
            query["shift_id"] = ObjectId(shift_id)
        except Exception:
            query["shift_id"] = shift_id
    if employee and employee.strip():
        # Audit filter: cashier who issued — matches the emission stamp's
        # employee label OR the IAM opener (case-insensitive contains).
        rx = {"$regex": re.escape(employee.strip()), "$options": "i"}
        query["$or"] = [{"shift_employee": rx}, {"shift_opened_by": rx}]

    total = db[INVOICES].count_documents(query)
    cursor = (
        db[INVOICES]
        .find(query)
        .sort("issued_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for doc in cursor:
        enriched = _enrich_invoice(doc)
        inv_id = enriched.get("id", "")
        booking_id_field = enriched.get("booking_id", "")
        pid = int(enriched.get("prop_id", 0))

        booking_doc = db.booking_orders.find_one(
            {"booking_id": booking_id_field},
            {"_id": 0, "guest_name": 1},
        )
        enriched["guest_name"] = (booking_doc or {}).get("guest_name", "") if booking_doc else ""

        if pid:
            hotel = db.dim_hotels.find_one(
                {"prop_id": pid},
                {"_id": 0, "display_name": 1, "hotel_name": 1},
            )
            enriched["hotel_label"] = (
                hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel #{pid}"
            ) if hotel else f"Hotel #{pid}"
        else:
            enriched["hotel_label"] = ""

        try:
            payments_cursor = db[PAYMENTS].find(
                {"invoice_id": ObjectId(inv_id), "status": "confirmed"},
                {"_id": 0, "amount": 1},
            )
            total_paid = round(sum(float(p.get("amount", 0)) for p in payments_cursor), 2)
        except Exception:
            logger.warning("Failed to fetch payments for invoice %s", inv_id)
            total_paid = 0.0
        enriched["total_paid_amount"] = total_paid
        status_value = str(enriched.get("status") or "").lower()
        effective_total = float(
            enriched.get("recognized_total")
            if enriched.get("recognized_total") is not None
            else (0.0 if status_value in {"cancelled", "refunded"} else enriched.get("total", 0) or 0)
        )
        enriched["total_pending_amount"] = round(max(effective_total - total_paid, 0), 2)

        if q:
            q_lower = q.lower()
            matches = (
                q_lower in booking_id_field.lower()
                or q_lower in enriched.get("guest_name", "").lower()
                or q_lower in enriched.get("invoice_number", "").lower()
            )
            if not matches:
                continue

        items.append(enriched)

    if q:
        total = len(items)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def get_invoice_stats(prop_id: int | None = None) -> dict:
    """Return counts and totals grouped by invoice status for one hotel."""
    db = get_database()
    match: dict[str, Any] = {}
    if prop_id is not None:
        match["prop_id"] = int(prop_id)
    pipeline = []
    if match:
        pipeline.append({"$match": match})
    pipeline.extend([
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "total_amount": {"$sum": {"$ifNull": ["$total", 0]}},
            },
        },
        {"$sort": {"_id": 1}},
    ])
    results = list(db[INVOICES].aggregate(pipeline))
    stats = {
        "issued": {"count": 0, "total": 0.0},
        "paid": {"count": 0, "total": 0.0},
        "cancelled": {"count": 0, "total": 0.0},
        "refunded": {"count": 0, "total": 0.0},
    }
    for r in results:
        key = r["_id"]
        if key in stats:
            stats[key]["count"] = r["count"]
            stats[key]["total"] = round(r["total_amount"], 2)
    return stats


def get_invoice(invoice_id: str) -> dict | None:
    db = get_database()
    try:
        from bson.errors import InvalidId
        doc = db[INVOICES].find_one({"_id": ObjectId(invoice_id)})
    except (InvalidId, Exception):
        return None
    if not doc:
        return None
    enriched = _enrich_invoice(doc)

    booking_id = enriched.get("booking_id", "")
    prop_id = int(enriched.get("prop_id", 0))

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "guest_name": 1, "guest_email": 1, "cedula": 1,
         "check_in_date": 1, "check_out_date": 1, "total_nights": 1,
         "rooms": 1, "room_type_id": 1, "assigned_rooms": 1,
         "check_in_time": 1, "check_out_time": 1},
    )
    if booking:
        enriched["guest_name"] = booking.get("guest_name", "")
        enriched["guest_email"] = booking.get("guest_email", "")
        enriched["guest_cedula"] = booking.get("cedula", "")
        enriched["check_in_date"] = booking.get("check_in_date", "")
        enriched["check_out_date"] = booking.get("check_out_date", "")
        enriched["check_in_time"] = booking.get("check_in_time") or ""
        enriched["check_out_time"] = booking.get("check_out_time") or ""
        enriched["total_nights"] = booking.get("total_nights", 1)
        enriched["rooms"] = booking.get("rooms", 1)
        room_type_id = booking.get("room_type_id", "")
        if room_type_id:
            rt = db.room_types.find_one(
                {"room_type_id": room_type_id, "prop_id": prop_id},
                {"_id": 0, "name": 1},
            )
            enriched["room_type_name"] = rt.get("name", room_type_id) if rt else room_type_id
        else:
            enriched["room_type_name"] = ""
        assigned_ids = booking.get("assigned_rooms") or []
        room_labels = []
        if assigned_ids:
            room_docs = list(
                db.hotel_rooms.find(
                    {"hotel_room_id": {"$in": assigned_ids}},
                    {"_id": 0, "room_label": 1},
                )
            )
            for r in room_docs:
                room_labels.append(r.get("room_label", ""))
        enriched["room_labels"] = room_labels

    if prop_id:
        hotel = db.dim_hotels.find_one(
            {"prop_id": prop_id},
            {"_id": 0, "display_name": 1, "hotel_name": 1},
        )
        enriched["hotel_label"] = (
            hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel #{prop_id}"
        ) if hotel else f"Hotel #{prop_id}"
    else:
        enriched["hotel_label"] = ""

    payments = list(
        db[PAYMENTS].find({"invoice_id": ObjectId(invoice_id)}).sort("paid_at", -1).limit(50)
    )
    enriched["payments"] = [_enrich_payment(p) for p in payments]

    total_paid = round(
        sum(float(p.get("amount", 0)) for p in payments if p.get("status") == "confirmed"), 2,
    )
    enriched["total_paid_amount"] = total_paid
    status_value = str(enriched.get("status") or "").lower()
    effective_total = float(
        enriched.get("recognized_total")
        if enriched.get("recognized_total") is not None
        else (0.0 if status_value in {"cancelled", "refunded"} else enriched.get("total", 0) or 0)
    )
    enriched["total_pending_amount"] = round(max(effective_total - total_paid, 0), 2)

    enriched["folio_id"] = None
    enriched["folio_number"] = None
    try:
        folio = db.guest_folios.find_one(
            {"booking_id": booking_id},
            {"_id": 1, "folio_number": 1},
        )
        if folio:
            enriched["folio_id"] = str(folio["_id"])
            enriched["folio_number"] = folio.get("folio_number")
    except Exception:
        logger.exception("Failed to fetch folio for booking %s", booking_id)

    return enriched


def add_line_item(
    invoice_id: str, *, name: str, quantity: int = 1,
    unit_price: float = 0.0, category: str = "Otros",
) -> dict | None:
    """Add a line item to an issued invoice and recalculate totals."""
    db = get_database()
    try:
        from bson.errors import InvalidId
        doc_id = ObjectId(invoice_id)
    except (InvalidId, Exception):
        return None

    # An issued invoice may be amended only before any confirmed payment.
    # Once money is applied, use a credit-note workflow instead of mutating
    # the fiscal snapshot underneath the payment.
    inv = db[INVOICES].find_one({"_id": doc_id, "status": "issued"})
    if not inv:
        return None
    if db[PAYMENTS].find_one({"invoice_id": doc_id, "status": {"$in": ["confirmed", "refunded"]}}):
        return None

    total = round(unit_price * quantity, 2)
    item_id = secrets.token_hex(8)
    new_item = {
        "item_id": item_id,
        "type": "manual_charge",
        "name": name,
        "quantity": quantity,
        "unit_price": round(unit_price, 2),
        "total": total,
        "category": category,
        "created_at": _now(),
    }

    existing_items = inv.get("line_items", []) or []
    combined = existing_items + [new_item]
    extras_total = round(sum(float(it.get("total", 0)) for it in combined), 2)
    room_subtotal = inv.get("room_subtotal", 0) or 0
    new_subtotal = round(room_subtotal + extras_total, 2)
    new_taxes = round(new_subtotal * 0.16, 2)
    new_total = round(new_subtotal + new_taxes, 2)

    update = {
        "$push": {"line_items": new_item},
        "$set": {
            "extras_total": extras_total,
            "subtotal": new_subtotal,
            "taxes": new_taxes,
            "total": new_total,
            "updated_at": _now(),
        },
    }
    result = db[INVOICES].find_one_and_update(
        {"_id": doc_id, "status": "issued"},
        update,
        return_document=ReturnDocument.AFTER,
    )
    if result:
        _update_both(INVOICES, FACT_INVOICES, doc_id, {"$set": {
            "extras_total": extras_total,
            "subtotal": new_subtotal,
            "taxes": new_taxes,
            "total": new_total,
            "line_items": combined,
            "updated_at": _now(),
        }})
    return _enrich_invoice(result) if result else None


def remove_line_item(invoice_id: str, item_id: str) -> dict | None:
    """Remove a line item from an issued invoice and recalculate totals."""
    db = get_database()
    try:
        from bson.errors import InvalidId
        doc_id = ObjectId(invoice_id)
    except (InvalidId, Exception):
        return None

    inv = db[INVOICES].find_one({"_id": doc_id, "status": "issued"})
    if not inv:
        return None
    if db[PAYMENTS].find_one({"invoice_id": doc_id, "status": {"$in": ["confirmed", "refunded"]}}):
        return None

    existing_items = inv.get("line_items", []) or []
    target = next((it for it in existing_items if it.get("item_id") == item_id), None)
    if not target:
        return None
    if target.get("type") == "room":
        return None

    remaining = [it for it in existing_items if it.get("item_id") != item_id]
    extras_total = round(sum(float(it.get("total", 0)) for it in remaining if it.get("type") != "room"), 2)
    room_subtotal = inv.get("room_subtotal", 0) or 0
    new_subtotal = round(room_subtotal + extras_total, 2)
    new_taxes = round(new_subtotal * 0.16, 2)
    new_total = round(new_subtotal + new_taxes, 2)

    update = {
        "$set": {
            "line_items": remaining,
            "extras_total": extras_total,
            "subtotal": new_subtotal,
            "taxes": new_taxes,
            "total": new_total,
            "updated_at": _now(),
        },
    }
    result = db[INVOICES].find_one_and_update(
        {"_id": doc_id, "status": "issued"},
        update,
        return_document=ReturnDocument.AFTER,
    )
    if result:
        _update_both(INVOICES, FACT_INVOICES, doc_id, {"$set": {
            "line_items": remaining,
            "extras_total": extras_total,
            "subtotal": new_subtotal,
            "taxes": new_taxes,
            "total": new_total,
            "updated_at": _now(),
        }})
    return _enrich_invoice(result) if result else None


def cancel_invoice(
    invoice_id: str,
    *,
    cancel_reason: str | None = None,
    cancelled_by: str | None = None,
    shift_id: str | None = None,
    shift_attribution: dict | None = None,
) -> dict | None:
    """Cancel an issued invoice, persisting the cancellation history on the doc.

    ``cancel_reason`` (motivo/nota de la anulación) y ``cancelled_by`` (quién
    la ejecutó) quedan guardados en Mongo sobre la factura y su espejo de
    hechos, para que la anulación sea auditable. Ambos son opcionales: una
    llamada sin ellos conserva el comportamiento legacy (sin campos extra).
    """
    db = get_database()
    try:
        from bson.errors import InvalidId
        doc_id = ObjectId(invoice_id)
    except (InvalidId, Exception):
        return None

    inv = db[INVOICES].find_one({"_id": doc_id}, {"status": 1})
    if not inv:
        return None

    # Validate with central StateMachine
    try:
        invoice_sm.validate_transition(inv.get("status", ""), "cancelled")
    except ValueError:
        return None

    now = _now()
    cancel_set: dict = {"status": "cancelled", "cancelled_at": now, "updated_at": now}
    # Historial auditable de la anulación: motivo/nota y quién la ejecutó. Solo
    # se escriben cuando se proveen, para no contaminar el doc legacy.
    normalized_reason = str(cancel_reason or "").strip() or None
    if normalized_reason:
        cancel_set["cancel_reason"] = normalized_reason
    if cancelled_by:
        cancel_set["cancelled_by"] = cancelled_by
    # Cashier attribution of the cancellation: the shift + employee that voided
    # the document, kept separate from the issuing shift so both attributions
    # survive on the doc (parity with refund_shift_* on payments).
    if shift_id:
        try:
            cancel_set["cancelled_shift_id"] = ObjectId(shift_id)
        except Exception:
            cancel_set["cancelled_shift_id"] = shift_id
        if shift_attribution:
            for key in ("shift_employee", "shift_opened_by", "shift_opened_by_id", "shift_type"):
                if shift_attribution.get(key):
                    cancel_set[f"cancelled_{key}"] = shift_attribution[key]

    doc = db[INVOICES].find_one_and_update(
        {"_id": doc_id, "status": inv["status"]},
        {"$set": cancel_set},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        _update_both(INVOICES, FACT_INVOICES, doc_id, {"$set": cancel_set})

        # Generate reversal double-entry ledger entries
        try:
            from src.app.modules.expenses.service.ledger_hooks import generate_reversal_from_invoice
            generate_reversal_from_invoice(doc)
        except Exception:
            logger.exception("Failed to generate ledger reversal for invoice %s", invoice_id)
        try:
            from src.app.modules.financial_reconciliation.domain_events import append_domain_event
            append_domain_event(
                prop_id=int(doc.get("prop_id", 0) or 0),
                event_type="guest_ar.invoice.cancelled",
                aggregate_type="guest_ar",
                aggregate_id=str(doc.get("invoice_number", invoice_id)),
                idempotency_key=f"live:invoice:cancelled:{doc.get('invoice_number', invoice_id)}",
                payload={"booking_id": doc.get("booking_id"), "total": doc.get("total", 0), "status": "cancelled"},
                source_collection=INVOICES,
                source_id=str(doc.get("invoice_number", invoice_id)),
            )
        except Exception:
            logger.exception("Failed to emit cancellation event for invoice %s", invoice_id)

    return _enrich_invoice(doc) if doc else None


def repair_cancelled_or_refunded_invoice(
    invoice_id: str,
    *,
    changed_by: str = "historical_reconciliation",
) -> dict | None:
    """Reconcile a voided/refunded invoice without erasing its fiscal value.

    The invoice's original ``total`` remains the immutable document amount;
    ``recognized_total=0`` is the current net value after cancellation or
    refund. The reversal journal is rebuilt only when missing, incomplete, or
    mismatched, and the same source key makes retries idempotent.
    """
    db = get_database()
    try:
        from bson.errors import InvalidId
        invoice_oid = ObjectId(invoice_id)
    except (InvalidId, Exception):
        return None

    invoice = db[INVOICES].find_one({"_id": invoice_oid})
    if not invoice or invoice.get("status") not in {"cancelled", "refunded"}:
        return None
    original_total = round(float(invoice.get("original_total", invoice.get("total", 0)) or 0), 2)
    if original_total <= 0:
        return None
    invoice_number = str(invoice.get("invoice_number") or "")
    if not invoice_number:
        return None

    reversal_query = {"source": "invoice_reversal", "source_id": invoice_number}
    reversal_rows = list(db.ledger_transactions.find(reversal_query, {"debit": 1, "credit": 1, "journal_entry_id": 1}))
    reversal_debit = round(sum(float(row.get("debit", 0) or 0) for row in reversal_rows), 2)
    reversal_credit = round(sum(float(row.get("credit", 0) or 0) for row in reversal_rows), 2)
    reversal_complete = (
        len(reversal_rows) >= 2
        and reversal_debit == original_total
        and reversal_credit == original_total
    )
    if not reversal_complete:
        if reversal_rows:
            db.ledger_transactions.delete_many(reversal_query)
        from src.app.modules.expenses.service.ledger_hooks import generate_reversal_from_invoice
        generate_reversal_from_invoice(invoice, db=db)
        reversal_rows = list(db.ledger_transactions.find(reversal_query, {"journal_entry_id": 1}))

    journal_ids = sorted({str(row.get("journal_entry_id")) for row in reversal_rows if row.get("journal_entry_id")})
    now = _now()
    update = {
        "original_total": original_total,
        "recognized_total": 0.0,
        "net_total": 0.0,
        "accounting_status": "reversed",
        "accounting_reversal_source": "invoice_reversal",
        "accounting_reversal_journal_id": journal_ids[0] if journal_ids else None,
        "accounting_repaired_at": now,
        "accounting_repaired_by": changed_by,
        "metadata.reconciliation": {
            "action": "reconciled_cancelled_or_refunded_invoice",
            "changed_by": changed_by,
            "changed_at": now,
            "original_total": original_total,
            "recognized_total": 0.0,
        },
        "updated_at": now,
    }
    db[INVOICES].update_one({"_id": invoice_oid}, {"$set": update})
    db[FACT_INVOICES].update_one({"_id": invoice_oid}, {"$set": update}, upsert=True)
    refreshed = db[INVOICES].find_one({"_id": invoice_oid})
    return _enrich_invoice(refreshed) if refreshed else None


def reconcile_positive_invoice_accounting(
    invoice_id: str,
    *,
    changed_by: str = "historical_reconciliation",
) -> dict | None:
    """Ensure one positive Guest AR invoice has a complete, traceable GL pair.

    This converges both live invoices and deterministic legacy repairs. Existing
    complete journals are reused; incomplete source rows are replaced before
    regeneration. The invoice, fact mirror, domain event and audit row all use
    stable identifiers, so retries cannot create duplicate revenue or evidence.
    """
    db = get_database()
    try:
        invoice_oid = ObjectId(invoice_id)
    except Exception:
        return None

    invoice = db[INVOICES].find_one({"_id": invoice_oid})
    if not invoice or float(invoice.get("total", 0) or 0) <= 0:
        return None
    if str(invoice.get("status") or "").lower() in {"cancelled", "refunded"}:
        return None

    invoice_number = str(invoice.get("invoice_number") or "")
    if not invoice_number:
        return None

    source_query = {"source": "invoice", "source_id": invoice_number}
    rows = list(db["ledger_transactions"].find(source_query, {"debit": 1, "credit": 1, "journal_entry_id": 1}))
    total = round(float(invoice.get("total", 0) or 0), 2)

    def trace_is_complete(entries: list[dict]) -> bool:
        if len(entries) < 2:
            return False
        journals = {str(row.get("journal_entry_id")) for row in entries if row.get("journal_entry_id")}
        debit = round(sum(float(row.get("debit", 0) or 0) for row in entries), 2)
        credit = round(sum(float(row.get("credit", 0) or 0) for row in entries), 2)
        return len(journals) == 1 and debit == total and credit == total

    if not trace_is_complete(rows):
        if rows:
            db["ledger_transactions"].delete_many(source_query)
        from src.app.modules.expenses.service.ledger_hooks import generate_ledger_from_invoice
        generate_ledger_from_invoice(invoice, db=db)
        rows = list(db["ledger_transactions"].find(source_query, {"debit": 1, "credit": 1, "journal_entry_id": 1}))

    now = _now()
    journals = sorted({str(row.get("journal_entry_id")) for row in rows if row.get("journal_entry_id")})
    posted = trace_is_complete(rows)
    status_update = {
        "accounting_status": "posted" if posted else "failed",
        "ledger_posting_status": "posted" if posted else "failed",
        "ledger_posting_error": None if posted else "El asiento no cubre el importe total de la factura",
        "ledger_references": journals,
        "accounting_reconciled_at": now,
        "accounting_reconciled_by": changed_by,
        "updated_at": now,
    }
    _update_both(INVOICES, FACT_INVOICES, invoice_oid, {"$set": status_update})
    # Legacy invoices may predate their fact mirror. Replace the mirror from
    # the committed operational snapshot so the accounting repair never leaves
    # a second source of truth or a missing analytical document.
    refreshed_for_mirror = db[INVOICES].find_one({"_id": invoice_oid})
    if refreshed_for_mirror:
        db[FACT_INVOICES].replace_one(
            {"_id": invoice_oid},
            dict(refreshed_for_mirror),
            upsert=True,
        )

    if posted:
        event_key = f"invoice-accounting-reconciliation:v1:{invoice_oid}"
        try:
            from src.app.modules.financial_reconciliation.domain_events import append_domain_event
            append_domain_event(
                prop_id=int(invoice.get("prop_id", 0) or 0),
                event_type="guest_ar.invoice.accounting_reconciled",
                aggregate_type="guest_ar",
                aggregate_id=str(invoice_oid),
                idempotency_key=event_key,
                payload={
                    "booking_id": invoice.get("booking_id"),
                    "invoice_number": invoice_number,
                    "total": total,
                    "ledger_references": journals,
                    "changed_by": changed_by,
                },
                source_collection=INVOICES,
                source_id=invoice_number,
                actor_id=changed_by,
            )
        except Exception:
            logger.exception("Failed to emit accounting reconciliation event %s", invoice_number)

        if not db.audit_log.find_one({
            "prop_id": int(invoice.get("prop_id", 0) or 0),
            "entity_type": "guest_ar_invoice",
            "entity_id": str(invoice_oid),
            "action": "accounting_reconciled",
        }):
            from src.app.modules.partner.services.audit import register_action
            register_action(
                prop_id=int(invoice.get("prop_id", 0) or 0),
                entity_type="guest_ar_invoice",
                entity_id=str(invoice_oid),
                action="accounting_reconciled",
                summary=f"Factura {invoice_number} conciliada con libro mayor",
                changed_by=changed_by,
                metadata={
                    "invoice_number": invoice_number,
                    "ledger_references": journals,
                    "amount": total,
                    "idempotency_key": event_key,
                },
            )

    refreshed = db[INVOICES].find_one({"_id": invoice_oid})
    return _enrich_invoice(refreshed) if refreshed else None


def update_invoice_additional_charges(
    booking_id: str, *, changed_by: str = "angular_api",
) -> dict | None:
    """Rebuild invoice extras from active charges and reconcile their ledger.

    This is deliberately a reconciliation, not an additive update: an edited
    or reversed charge must disappear from invoice extras on the next retry.
    The invoice and its fact mirror are updated from the same calculated
    snapshot, while one idempotent compensating ledger pair represents the
    current delta from the original invoice journal.
    """
    from src.app.modules.housekeeping.service.collections import CHARGES_COLLECTION

    db = get_database()

    # Only active charges belong to the customer invoice. Reversed charges
    # remain in Mongo as audit evidence but must not continue contributing to
    # revenue, invoice totals, booking totals, or reconciliation dashboards.
    charges = list(db[CHARGES_COLLECTION].find({
        "booking_id": booking_id,
        "status": {"$ne": "reversed"},
    }).sort("_id", 1))
    charges_sum = round(sum(float(c.get("total", 0) or 0) for c in charges), 2)

    if not charges and not db[INVOICES].find_one({"booking_id": booking_id}):
        return None

    inv = db[INVOICES].find_one({"booking_id": booking_id})
    if not inv:
        return None

    # A confirmed or refunded payment makes the fiscal snapshot immutable.
    # Rebuilding extras after money has been applied would change the amount
    # against which the payment was settled. Use a credit-note/compensating
    # invoice workflow instead of silently changing this invoice.
    if inv.get("status") in {"paid", "partially_paid", "refunded", "cancelled"} or db[PAYMENTS].find_one({
        "invoice_id": inv["_id"],
        "status": {"$in": ["confirmed", "refunded"]},
    }, {"_id": 1}):
        raise ValueError("La factura no puede reconstruirse después de pagos confirmados")

    inv_id = inv["_id"]

    charge_items = []
    for c in charges:
        charge_items.append({
            "type": "additional_charge",
            "charge_id": str(c.get("_id", "")),
            "concept": c.get("concept", ""),
            "amount": c.get("amount", 0),
            "quantity": c.get("quantity", 1),
            "total": c.get("total", 0),
            "created_at": c.get("created_at", ""),
        })

    existing_line_items = inv.get("line_items", []) or []
    preserved_items = [
        item for item in existing_line_items
        if not (isinstance(item, dict) and item.get("type") == "additional_charge")
    ]
    combined_line_items = preserved_items + charge_items

    room_subtotal = float(inv.get("room_subtotal", 0) or 0)
    # Keep the non-charge extras (e.g. product services) and replace only the
    # additional-charge component instead of adding the whole charge sum again.
    non_charge_extras = round(sum(
        float(item.get("total", 0) or 0)
        for item in preserved_items
        if isinstance(item, dict) and item.get("type") != "room"
    ), 2)
    new_extras = round(non_charge_extras + charges_sum, 2)
    new_subtotal = round(room_subtotal + new_extras, 2)
    new_taxes = round(new_subtotal * 0.16, 2)
    new_total = round(new_subtotal + new_taxes, 2)

    update_doc = {
        "extras_total": new_extras,
        "subtotal": new_subtotal,
        "taxes": new_taxes,
        "total": new_total,
        "line_items": combined_line_items,
        "additional_charges": [
            {
                "charge_id": str(c.get("_id", "")),
                "concept": c.get("concept", ""),
                "amount": c.get("amount", 0),
                "quantity": c.get("quantity", 1),
                "total": c.get("total", 0),
            }
            for c in charges
        ],
        "updated_at": _now(),
    }

    # Atomic replacement of the invoice snapshot. This is intentionally not
    # an increment: retries, edits and reversals all converge to the same
    # result.
    new_charge_total = round(charges_sum, 2)
    old_charge_total = round(sum(
        float(item.get("total", 0) or 0)
        for item in existing_line_items
        if isinstance(item, dict) and item.get("type") == "additional_charge"
    ), 2)

    db[INVOICES].update_one({"_id": inv_id}, {"$set": update_doc})
    db[FACT_INVOICES].update_one({"_id": inv_id}, {"$set": update_doc})

    non_charge_booking_total = _booking_total_without_additional_charges(
        db, booking_id, old_charge_total,
    )
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {
            "total_charges": round(non_charge_booking_total + new_charge_total, 2),
            "updated_at": _now(),
        }},
    )

    # Reconcile the ledger delta against the invoice's original extras. The
    # same source key is replaced atomically so a retry cannot double-post and
    # a void removes the compensating pair instead of leaving stale revenue.
    ledger_source = "invoice_additional_charge_adjustment"
    ledger_source_id = str(inv.get("invoice_number", inv_id))
    ledger_status = "posted"
    ledger_error = None
    try:
        db.ledger_transactions.delete_many({
            "source": ledger_source,
            "source_id": ledger_source_id,
        })
        if new_charge_total > 0:
            from src.app.modules.expenses.service.ledger_hooks import post_journal_entry
            post_journal_entry(
                amount=new_charge_total,
                dr_account_code="1030",
                dr_account_name="Cuentas por Cobrar Huéspedes",
                cr_account_code="4030",
                cr_account_name="Ingresos por Servicios",
                description=f"Ajuste de consumos — Factura {ledger_source_id}",
                prop_id=int(inv.get("prop_id", 0) or 0),
                source=ledger_source,
                source_id=ledger_source_id,
                booking_id=booking_id,
            )
    except Exception as exc:
        # The invoice snapshot remains useful, but its accounting projection
        # must be visibly retryable instead of looking posted when the ledger
        # writer is unavailable.
        ledger_status = "failed"
        ledger_error = str(exc)

    db[INVOICES].update_one({"_id": inv_id}, {"$set": {
        "ledger_posting_status": ledger_status,
        "ledger_posting_error": ledger_error,
        "updated_at": _now(),
    }})
    db[FACT_INVOICES].update_one({"_id": inv_id}, {"$set": {
        "ledger_posting_status": ledger_status,
        "ledger_posting_error": ledger_error,
        "updated_at": _now(),
    }})

    if old_charge_total != new_charge_total or not existing_line_items:
        db.booking_status_history.insert_one({
            "booking_id": booking_id,
            "status": "settled_charges",
            "changed_at": _now(),
            "reason": f"Consumo liquidado: {len(charges)} cargo(s) por ${charges_sum:.2f}",
            "changed_by": changed_by,
            "is_test": False,
        })

    updated = db[INVOICES].find_one({"_id": inv_id})
    return _enrich_invoice(updated) if updated else None


def create_split_charges_invoice(
    booking_id: str, *, changed_by: str = "angular_api",
) -> dict | None:
    """Create a separate invoice for additional charges only (split by charge type)."""
    from src.app.modules.housekeeping.service.collections import CHARGES_COLLECTION

    db = get_database()

    # A reversed charge remains auditable but must never enter a new invoice.
    charges = list(db[CHARGES_COLLECTION].find({
        "booking_id": booking_id,
        "status": {"$ne": "reversed"},
    }).sort("_id", 1))
    charges_sum = round(sum(float(c.get("total", 0) or 0) for c in charges), 2)

    booking = _find_booking(booking_id)
    if not booking:
        return None

    existing_split = db[INVOICES].find_one({
        "booking_id": booking_id,
        "split_type": "charges_only",
        "status": {"$ne": "cancelled"},
    })
    # Once every source charge is reversed, the existing split invoice is a
    # stale receivable projection. Cancel it (and its mirror) while retaining
    # the original ledger evidence plus a compensating reversal.
    if existing_split and not charges:
        if existing_split.get("status") in {"paid", "partially_paid", "refunded"} or db[PAYMENTS].find_one({
            "invoice_id": existing_split["_id"],
            "status": {"$in": ["confirmed", "refunded"]},
        }, {"_id": 1}):
            # The paid snapshot is immutable. Reversing the source charge is
            # now a credit-note/compensating-document concern, not a silent
            # cancellation of the receivable.
            raise ValueError("La factura split pagada requiere un documento compensatorio")
        if existing_split.get("status") == "issued":
            try:
                from src.app.modules.expenses.service.ledger_hooks import generate_reversal_from_invoice
                reversal_query = {
                    "source": "invoice_reversal",
                    "source_id": existing_split.get("invoice_number", ""),
                }
                reversal_rows = list(db.ledger_transactions.find(
                    reversal_query, {"debit": 1, "credit": 1},
                ))
                reversal_debit = round(sum(float(row.get("debit", 0) or 0) for row in reversal_rows), 2)
                reversal_credit = round(sum(float(row.get("credit", 0) or 0) for row in reversal_rows), 2)
                reversal_complete = (
                    len(reversal_rows) >= 2
                    and reversal_debit > 0
                    and reversal_debit == reversal_credit
                )
                if reversal_rows and not reversal_complete:
                    # A crash may leave one side of the compensating journal.
                    # Remove only that incomplete source event, then rebuild it
                    # idempotently on the injected database.
                    db.ledger_transactions.delete_many(reversal_query)
                reversal_count = generate_reversal_from_invoice(existing_split, db=db)
                reversal_rows = list(db.ledger_transactions.find(
                    reversal_query, {"debit": 1, "credit": 1},
                ))
                reversal_debit = round(sum(float(row.get("debit", 0) or 0) for row in reversal_rows), 2)
                reversal_credit = round(sum(float(row.get("credit", 0) or 0) for row in reversal_rows), 2)
                reversal_complete = (
                    len(reversal_rows) >= 2
                    and reversal_debit > 0
                    and reversal_debit == reversal_credit
                )
                if not reversal_count and not reversal_complete:
                    raise RuntimeError("no se generó el asiento de reverso")
            except Exception as exc:
                logger.exception("Failed to reverse empty split invoice %s", existing_split.get("invoice_number"))
                raise ValueError("No se puede cancelar la factura split sin un reverso contable") from exc
            db[INVOICES].update_one({"_id": existing_split["_id"]}, {"$set": {
                "status": "cancelled",
                "subtotal": 0.0,
                "room_subtotal": 0.0,
                "extras_total": 0.0,
                "taxes": 0.0,
                "total": 0.0,
                "line_items": [],
                "additional_charges": [],
                "charge_snapshot": [],
                "updated_at": _now(),
            }})
            db[FACT_INVOICES].update_one({"_id": existing_split["_id"]}, {"$set": {
                "status": "cancelled",
                "subtotal": 0.0,
                "room_subtotal": 0.0,
                "extras_total": 0.0,
                "taxes": 0.0,
                "total": 0.0,
                "line_items": [],
                "additional_charges": [],
                "charge_snapshot": [],
                "updated_at": _now(),
            }})
        non_charge_booking_total = _booking_total_without_additional_charges(
            db, booking_id, float(existing_split.get("extras_total", 0) or 0),
        )
        db.booking_orders.update_one({"booking_id": booking_id}, {"$set": {
            "total_charges": non_charge_booking_total,
            "updated_at": _now(),
        }})
        return None

    if not charges:
        return None

    charge_snapshot = [
        {
            "charge_id": str(c.get("_id", "")),
            "amount": round(float(c.get("amount", 0) or 0), 2),
            "quantity": int(c.get("quantity", 1) or 1),
            "total": round(float(c.get("total", 0) or 0), 2),
        }
        for c in charges
    ]
    if existing_split:
        if existing_split.get("charge_snapshot") == charge_snapshot:
            return _enrich_invoice(existing_split)
        if existing_split.get("status") in {"paid", "partially_paid", "refunded"} or db[PAYMENTS].find_one({
            "invoice_id": existing_split["_id"],
            "status": {"$in": ["confirmed", "refunded"]},
        }, {"_id": 1}):
            raise ValueError("La factura split no puede reconstruirse después de pagos confirmados")

        # Before payment, an issued split invoice is a projection of the
        # active charge set. Rebuild that projection in place rather than
        # creating a second invoice on a checkout retry.
        updated_split = {
            "subtotal": charges_sum,
            "room_subtotal": 0,
            "extras_total": charges_sum,
            "taxes": round(charges_sum * 0.16, 2),
            "total": round(charges_sum * 1.16, 2),
            "line_items": [
                {
                    "type": "additional_charge",
                    "charge_id": str(c.get("_id", "")),
                    "concept": c.get("concept", "") or c.get("item_name", ""),
                    "amount": c.get("amount", 0),
                    "quantity": c.get("quantity", 1),
                    "total": c.get("total", 0),
                    "created_at": c.get("created_at", ""),
                }
                for c in charges
            ],
            "additional_charges": [
                {
                    "charge_id": str(c.get("_id", "")),
                    "concept": c.get("concept", "") or c.get("item_name", ""),
                    "amount": c.get("amount", 0),
                    "quantity": c.get("quantity", 1),
                    "total": c.get("total", 0),
                }
                for c in charges
            ],
            "charge_snapshot": charge_snapshot,
            "notes": f"Factura de consumos — {len(charges)} cargo(s) adicional(es) por ${charges_sum:.2f}",
            "ledger_posting_status": "pending",
            "ledger_posting_error": None,
            "updated_at": _now(),
        }
        db[INVOICES].update_one({"_id": existing_split["_id"]}, {"$set": updated_split})
        db[FACT_INVOICES].update_one({"_id": existing_split["_id"]}, {"$set": updated_split})
        try:
            from src.app.modules.expenses.service.ledger_hooks import generate_ledger_from_invoice
            db.ledger_transactions.delete_many({
                "source": "invoice",
                "source_id": existing_split.get("invoice_number", ""),
            })
            refreshed_split = db[INVOICES].find_one({"_id": existing_split["_id"]}) or {}
            generate_ledger_from_invoice(refreshed_split, db=db)
            db[INVOICES].update_one({"_id": existing_split["_id"]}, {"$set": {
                "ledger_posting_status": "posted", "ledger_posting_error": None,
            }})
            db[FACT_INVOICES].update_one({"_id": existing_split["_id"]}, {"$set": {
                "ledger_posting_status": "posted", "ledger_posting_error": None,
            }})
        except Exception as exc:
            logger.exception("Failed to reconcile split invoice %s", existing_split.get("invoice_number", ""))
            db[INVOICES].update_one({"_id": existing_split["_id"]}, {"$set": {
                "ledger_posting_status": "failed", "ledger_posting_error": str(exc),
            }})
            db[FACT_INVOICES].update_one({"_id": existing_split["_id"]}, {"$set": {
                "ledger_posting_status": "failed", "ledger_posting_error": str(exc),
            }})
        non_charge_booking_total = _booking_total_without_additional_charges(
            db, booking_id, float(existing_split.get("extras_total", 0) or 0),
        )
        db.booking_orders.update_one({"booking_id": booking_id}, {"$set": {
            "total_charges": round(non_charge_booking_total + charges_sum, 2),
            "updated_at": _now(),
        }})
        updated = db[INVOICES].find_one({"_id": existing_split["_id"]})
        return _enrich_invoice(updated) if updated else None

    room_inv = db[INVOICES].find_one({"booking_id": booking_id, "split_type": {"$ne": "charges_only"}})
    room_inv_id = room_inv["_id"] if room_inv else None

    charge_items = []
    for c in charges:
        charge_items.append({
            "type": "additional_charge",
            "charge_id": str(c.get("_id", "")),
            "concept": c.get("concept", "") or c.get("item_name", ""),
            "amount": c.get("amount", 0),
            "quantity": c.get("quantity", 1),
            "total": c.get("total", 0),
            "created_at": c.get("created_at", ""),
        })

    extras_total = charges_sum
    subtotal = charges_sum
    taxes = round(subtotal * 0.16, 2)
    total = round(subtotal + taxes, 2)

    inv_doc = {
        "booking_id": booking.get("booking_id") or booking_id,
        "prop_id": booking.get("prop_id", 0),
        "hotel_id": resolve_hotel_id(booking.get("prop_id", 0)),
        "invoice_number": _generate_invoice_number(),
        "subtotal": subtotal,
        "room_subtotal": 0,
        "extras_total": extras_total,
        "line_items": charge_items,
        "taxes": taxes,
        "total": total,
        "status": "issued",
        "split_type": "charges_only",
        "parent_invoice_id": str(room_inv_id) if room_inv_id else None,
        "notes": f"Factura de consumos — {len(charges)} cargo(s) adicional(es) por ${charges_sum:.2f}",
        "additional_charges": [
            {
                "charge_id": str(c.get("_id", "")),
                "concept": c.get("concept", "") or c.get("item_name", ""),
                "amount": c.get("amount", 0),
                "quantity": c.get("quantity", 1),
                "total": c.get("total", 0),
            }
            for c in charges
        ],
        "charge_snapshot": charge_snapshot,
        "issued_at": _now(),
        "paid_at": None,
    }
    _write_both(INVOICES, FACT_INVOICES, inv_doc)

    # Split invoices are still guest receivables and must enter the same
    # accounting chain as the room invoice. Keep the projection observable so
    # a transient ledger failure can be retried without creating another bill.
    ledger_status = "posted"
    ledger_error = None
    try:
        from src.app.modules.expenses.service.ledger_hooks import generate_ledger_from_invoice
        generate_ledger_from_invoice(inv_doc, db=db)
    except Exception as exc:
        ledger_status = "failed"
        ledger_error = str(exc)
        logger.exception("Failed to generate ledger for split invoice %s", inv_doc.get("invoice_number", ""))
    db[INVOICES].update_one({"invoice_number": inv_doc["invoice_number"]}, {"$set": {
        "ledger_posting_status": ledger_status,
        "ledger_posting_error": ledger_error,
        "updated_at": _now(),
    }})
    db[FACT_INVOICES].update_one({"invoice_number": inv_doc["invoice_number"]}, {"$set": {
        "ledger_posting_status": ledger_status,
        "ledger_posting_error": ledger_error,
        "updated_at": _now(),
    }})

    if room_inv_id:
        db[INVOICES].update_one(
            {"_id": room_inv_id},
            {"$set": {
                "split_type": "room_only",
                "split_charges_invoice_id": str(inv_doc.get("_id") or inv_doc.get("inserted_id", "")),
                "updated_at": _now(),
            }},
        )
        db[FACT_INVOICES].update_one(
            {"_id": room_inv_id},
            {"$set": {
                "split_type": "room_only",
                "split_charges_invoice_id": str(inv_doc.get("_id") or inv_doc.get("inserted_id", "")),
                "updated_at": _now(),
            }},
        )

    non_charge_booking_total = _booking_total_without_additional_charges(
        db, booking_id, charges_sum,
    )
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {
            "total_charges": round(non_charge_booking_total + charges_sum, 2),
            "split_invoice": True,
            "updated_at": _now(),
        }},
    )

    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": "split_charges_invoice",
        "changed_at": _now(),
        "reason": f"Factura de consumos separada creada: {len(charges)} cargo(s) por ${charges_sum:.2f}",
        "changed_by": changed_by,
        "is_test": False,
    })

    updated = db[INVOICES].find_one({"invoice_number": inv_doc["invoice_number"]})
    return _enrich_invoice(updated) if updated else None
