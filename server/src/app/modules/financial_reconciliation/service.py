"""Read-only reconciliation rules for one hotel.

This module deliberately has no writes, audit inserts, repairs, or migrations.
It inspects only documents carrying the requested ``prop_id`` and returns
stable findings that can later be resolved by a separate, explicitly
privileged workflow.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from bson.decimal128 import Decimal128

from src.database.connection import get_database

_SEVERITIES = ("info", "warning", "critical")
_REPAIR_POLICIES = ("manual", "idempotent_migration", "not_repairable")


def _amount(value: Any) -> float:
    """Convert Mongo numeric values to a JSON-safe rounded amount."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal128):
        return round(float(value.to_decimal()), 2)
    if isinstance(value, Decimal):
        return round(float(value), 2)
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def _source_id(value: Any) -> str:
    return str(value) if value is not None else "unknown"


def _stable_finding_id(domain: str, key: str) -> str:
    digest = hashlib.sha1(f"{domain}:{key}".encode()).hexdigest()[:12]
    return f"REC-{domain.upper()}-{digest}"


def _finding(
    *,
    domain: str,
    severity: str,
    source_ids: list[Any],
    expected: dict[str, Any],
    actual: dict[str, Any],
    repair_policy: str,
    message: str,
) -> dict[str, Any]:
    if severity not in _SEVERITIES:
        raise ValueError(f"Unsupported reconciliation severity: {severity}")
    if repair_policy not in _REPAIR_POLICIES:
        raise ValueError(f"Unsupported repair policy: {repair_policy}")
    normalized_ids = [_source_id(value) for value in source_ids]
    stable_key = "|".join(normalized_ids)
    return {
        "finding_id": _stable_finding_id(domain, stable_key),
        "domain": domain,
        "severity": severity,
        "source_ids": normalized_ids,
        "expected": expected,
        "actual": actual,
        "resolution": "pending",
        "repair_policy": repair_policy,
        "message": message,
    }


def _invoice_ledger_totals(db, prop_id: int, invoice_number: str) -> tuple[float, float, int, int]:
    rows = list(db.ledger_transactions.find(
        {"prop_id": prop_id, "source": "invoice", "source_id": invoice_number},
        {"debit": 1, "credit": 1, "journal_entry_id": 1},
    ))
    return (
        round(sum(_amount(row.get("debit")) for row in rows), 2),
        round(sum(_amount(row.get("credit")) for row in rows), 2),
        len(rows),
        len({row.get("journal_entry_id") for row in rows if row.get("journal_entry_id")}),
    )


def _has_folio_posting_for_charge(folio: dict[str, Any], charge_id: Any) -> bool:
    charge_key = _source_id(charge_id)
    for posting in folio.get("postings", []) or []:
        reference_id = posting.get("reference_id")
        if _source_id(reference_id) == charge_key:
            return True
    return False


def build_reconciliation_report(prop_id: int) -> dict[str, Any]:
    """Build a read-only reconciliation snapshot for exactly one property.

    The query boundary is intentionally repeated on every collection. A
    missing ``prop_id`` is not treated as belonging to this hotel and therefore
    cannot leak into the result or contaminate its totals.
    """
    db = get_database()
    findings: list[dict[str, Any]] = []

    # Closed folios with a balance are findings, never automatic repairs.
    for folio in db.guest_folios.find(
        {"prop_id": prop_id, "status": "closed", "total_due": {"$gt": 0}},
        {"booking_id": 1, "folio_number": 1, "total_due": 1, "_id": 1},
    ).sort("_id", 1):
        folio_id = _source_id(folio.get("_id"))
        findings.append(_finding(
            domain="folio",
            severity="critical",
            source_ids=[folio_id, folio.get("booking_id")],
            expected={"status": "settled_or_exception_documented", "total_due": 0.0},
            actual={"status": folio.get("status"), "total_due": _amount(folio.get("total_due"))},
            repair_policy="manual",
            message="Folio cerrado con saldo pendiente; requiere conciliación manual.",
        ))

    # Failed attempts are useful evidence but not an unapplied confirmed cash
    # movement. Report them as info; confirmed/refunded payments without an
    # valid same-hotel invoice are warnings because their target cannot be
    # traced reliably.
    for payment in db.reservation_payments.find(
        {"prop_id": prop_id},
        {"booking_id": 1, "invoice_id": 1, "amount": 1, "status": 1, "method": 1, "_id": 1},
    ).sort("_id", 1):
        invoice_ref = payment.get("invoice_id")
        referenced_invoice = None
        if invoice_ref not in (None, ""):
            referenced_invoice = db.reservation_invoices.find_one(
                {"prop_id": prop_id, "$or": [{"_id": invoice_ref}, {"invoice_number": invoice_ref}]},
                {"_id": 1},
            )
        if invoice_ref not in (None, "") and referenced_invoice is not None:
            continue
        status = str(payment.get("status") or "unknown").lower()
        severity = "info" if status in {"failed", "rejected", "declined", "error"} else "warning"
        findings.append(_finding(
            domain="payment",
            severity=severity,
            source_ids=[payment.get("_id"), payment.get("booking_id")],
            expected={"invoice_id": "present_for_confirmed_or_refunded_payment"},
            actual={
                "invoice_id": invoice_ref,
                "status": payment.get("status"),
                "method": payment.get("method"),
                "amount": _amount(payment.get("amount")),
            },
            repair_policy="manual",
            message=(
                "Intento de pago fallido sin factura asociada; no altera saldo."
                if severity == "info"
                else (
                    "Pago confirmado/reembolsado con factura inexistente o fuera del hotel."
                    if invoice_ref not in (None, "")
                    else "Pago confirmado/reembolsado sin factura asociada."
                )
            ),
        ))

    # Positive guest invoices must have an invoice-origin ledger posting. Zero
    # invoices are not treated as missing revenue postings.
    for invoice in db.reservation_invoices.find(
        {"prop_id": prop_id, "total": {"$gt": 0}},
        {"invoice_number": 1, "total": 1, "status": 1, "_id": 1},
    ).sort("_id", 1):
        invoice_number = invoice.get("invoice_number")
        if not invoice_number:
            findings.append(_finding(
                domain="invoice",
                severity="warning",
                source_ids=[invoice.get("_id")],
                expected={"invoice_number": "present"},
                actual={"invoice_number": None, "total": _amount(invoice.get("total"))},
                repair_policy="manual",
                message="Factura positiva sin número fiscal para enlazar el libro mayor.",
            ))
            continue
        debit_total, credit_total, ledger_rows, journal_count = _invoice_ledger_totals(
            db, prop_id, str(invoice_number)
        )
        invoice_total = _amount(invoice.get("total"))
        if ledger_rows == 0:
            findings.append(_finding(
                domain="invoice",
                severity="critical",
                source_ids=[invoice.get("_id"), invoice_number],
                expected={"ledger_source": "invoice", "ledger_rows": ">=1"},
                actual={
                    "invoice_number": invoice_number,
                    "invoice_total": _amount(invoice.get("total")),
                    "ledger_rows": 0,
                },
                repair_policy="idempotent_migration",
                message="Factura positiva sin asiento de ingreso; revisar antes de reparar.",
            ))
        elif journal_count != 1 or abs(debit_total - credit_total) >= 0.01 or abs(credit_total - invoice_total) >= 0.01:
            findings.append(_finding(
                domain="invoice",
                severity="critical",
                source_ids=[invoice.get("_id"), invoice_number],
                expected={"ledger_credit": invoice_total, "ledger_balanced": True, "journal_count": 1},
                actual={
                    "invoice_total": invoice_total,
                    "ledger_debit": debit_total,
                    "ledger_credit": credit_total,
                    "ledger_difference": round(debit_total - credit_total, 2),
                    "journal_count": journal_count,
                },
                repair_policy="manual",
                message="El asiento de la factura no concilia importe o partida doble.",
            ))

    # Ledger must balance for this hotel; an empty ledger is balanced by
    # arithmetic but does not produce a spurious finding.
    ledger_totals = list(db.ledger_transactions.aggregate([
        {"$match": {"prop_id": prop_id}},
        {"$group": {
            "_id": None,
            "debit": {"$sum": "$debit"},
            "credit": {"$sum": "$credit"},
            "count": {"$sum": 1},
        }},
    ]))
    ledger_data = ledger_totals[0] if ledger_totals else {"debit": 0, "credit": 0, "count": 0}
    debit = _amount(ledger_data.get("debit"))
    credit = _amount(ledger_data.get("credit"))
    ledger_diff = round(debit - credit, 2)
    if ledger_data.get("count", 0) and abs(ledger_diff) >= 0.01:
        findings.append(_finding(
            domain="ledger",
            severity="critical",
            source_ids=[f"prop:{prop_id}"],
            expected={"debit": credit, "credit": debit, "difference": 0.0},
            actual={"debit": debit, "credit": credit, "difference": ledger_diff},
            repair_policy="manual",
            message="El libro mayor del hotel no balancea; no se debe corregir automáticamente.",
        ))

    # Additional charges should be traceable to a posting in their booking's
    # folio. Missing folio/booking is itself a finding; no writes are made.
    folio_by_booking = {
        folio.get("booking_id"): folio
        for folio in db.guest_folios.find(
            {"prop_id": prop_id, "booking_id": {"$exists": True}},
            {"booking_id": 1, "postings": 1, "_id": 1},
        )
    }
    for charge in db.additional_charges.find(
        {"prop_id": prop_id},
        {"booking_id": 1, "amount": 1, "description": 1, "_id": 1},
    ).sort("_id", 1):
        booking_id = charge.get("booking_id")
        folio = folio_by_booking.get(booking_id)
        if folio is None or not _has_folio_posting_for_charge(folio, charge.get("_id")):
            findings.append(_finding(
                domain="charge",
                severity="critical" if folio is None else "warning",
                source_ids=[charge.get("_id"), booking_id],
                expected={"folio_posting": "present"},
                actual={
                    "folio_id": _source_id(folio.get("_id")) if folio else None,
                    "amount": _amount(charge.get("amount")),
                    "description": charge.get("description"),
                },
                repair_policy="manual",
                message="Cargo adicional sin posting trazable en el folio.",
            ))

    # Current maintenance documents are operationally valid but financially
    # incomplete when they lack cost/invoice/ledger evidence.
    for task in db.maintenance_tasks.find(
        {"prop_id": prop_id, "status": {"$ne": "deleted"}},
        {"cost": 1, "actual_cost": 1, "expense_invoice_id": 1, "ledger_journal_id": 1, "room_id": 1, "_id": 1},
    ).sort("_id", 1):
        if not task.get("cost") and not task.get("actual_cost") and not task.get("expense_invoice_id") and not task.get("ledger_journal_id"):
            findings.append(_finding(
                domain="maintenance",
                severity="warning",
                source_ids=[task.get("_id"), task.get("room_id")],
                expected={"cost_or_financial_link": "present_when_costed"},
                actual={"cost": 0.0, "expense_invoice_id": None, "ledger_journal_id": None},
                repair_policy="manual",
                message="Mantenimiento sin coste o vínculo financiero; no permite calcular su impacto.",
            ))

    findings.sort(key=lambda item: item["finding_id"])
    severity_counts = {severity: sum(1 for item in findings if item["severity"] == severity) for severity in _SEVERITIES}
    domain_counts: dict[str, int] = {}
    for item in findings:
        domain_counts[item["domain"]] = domain_counts.get(item["domain"], 0) + 1

    return {
        "prop_id": int(prop_id),
        "as_of": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_findings": len(findings),
            "by_severity": severity_counts,
            "by_domain": dict(sorted(domain_counts.items())),
            "ledger": {
                "debit": debit,
                "credit": credit,
                "difference": ledger_diff,
                "is_balanced": abs(ledger_diff) < 0.01,
                "transaction_count": int(ledger_data.get("count", 0)),
            },
        },
        "findings": findings,
    }
