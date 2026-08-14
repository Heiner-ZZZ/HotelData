"""Read-only reconciliation rules for one hotel.

This module deliberately has no writes, audit inserts, repairs, or migrations.
It inspects only documents carrying the requested ``prop_id`` and returns
stable findings that can later be resolved by a separate, explicitly
privileged workflow.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone
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


def _balanced_source_rows(db: Any, query: dict[str, Any]) -> bool:
    """Return whether a source has a balanced journal in this hotel."""
    rows = list(db.ledger_transactions.find(
        query,
        {"debit": 1, "credit": 1, "journal_entry_id": 1},
    ))
    if len(rows) < 2:
        return False
    debit = round(sum(_amount(row.get("debit")) for row in rows), 2)
    credit = round(sum(_amount(row.get("credit")) for row in rows), 2)
    journals = {str(row.get("journal_entry_id")) for row in rows if row.get("journal_entry_id")}
    return debit > 0 and debit == credit and len(journals) == 1


def _historical_invoice_has_evidence(db: Any, prop_id: int, invoice: dict[str, Any]) -> bool:
    """Recognize non-duplicating accounting evidence for a reconstructed invoice.

    Historical invoices intentionally do not always create a second
    ``source=invoice`` revenue journal: they may reuse the original invoice
    plus its reversal, or rely on the already-posted folio room/charge events.
    They are valid only when the linked settled folio reconciles to the invoice
    total and at least one of those source trails is balanced.
    """
    if invoice.get("source") != "historical_reconstruction" or invoice.get("accounting_status") != "posted":
        return False

    folio_query: dict[str, Any] = {"prop_id": prop_id}
    folio_id = invoice.get("folio_id")
    if folio_id is not None:
        folio_query["_id"] = folio_id
    else:
        folio_query["booking_id"] = invoice.get("booking_id")
    folio = db.guest_folios.find_one(folio_query)
    if not folio or folio.get("status") not in {"settled", "closed", "written_off"}:
        return False
    if _amount(folio.get("total_due")) > 0.005:
        return False

    invoice_total = _amount(invoice.get("total"))
    folio_total = round(
        _amount(folio.get("total_room"))
        + _amount(folio.get("total_charges"))
        - _amount(folio.get("total_discounts")),
        2,
    )
    if abs(folio_total - invoice_total) >= 0.01:
        return False

    booking_id = str(invoice.get("booking_id") or "")
    evidence_groups: dict[tuple[str, str, str], list[float]] = {}
    for row in db.ledger_transactions.find(
        {
            "prop_id": prop_id,
            "booking_id": booking_id,
            "source": {"$in": ["historical_invoice", "folio_posting", "folio_transfer"]},
        },
        {"source": 1, "source_id": 1, "journal_entry_id": 1, "debit": 1, "credit": 1},
    ):
        key = (
            str(row.get("source") or ""),
            str(row.get("source_id") or ""),
            str(row.get("journal_entry_id") or ""),
        )
        evidence_groups.setdefault(key, [0.0, 0.0])
        evidence_groups[key][0] += _amount(row.get("debit"))
        evidence_groups[key][1] += _amount(row.get("credit"))

    evidence_total = 0.0
    for (source, source_id, _journal_id), (debit, credit) in evidence_groups.items():
        amount = max(round(debit, 2), round(credit, 2))
        if amount <= 0 or round(debit, 2) != round(credit, 2):
            continue
        sign = -1.0 if source == "folio_transfer" and source_id.startswith("XFR-OUT") else 1.0
        evidence_total += sign * amount
    if abs(round(evidence_total, 2) - invoice_total) < 0.01:
        return True

    legacy_id = invoice.get("supersedes_invoice_id")
    legacy = db.reservation_invoices.find_one({"_id": legacy_id, "prop_id": prop_id}) if legacy_id else None
    legacy_number = str((legacy or {}).get("invoice_number") or "")
    return bool(
        legacy_number
        and _balanced_source_rows(db, {"prop_id": prop_id, "source": "invoice", "source_id": legacy_number})
        and _balanced_source_rows(db, {"prop_id": prop_id, "source": "invoice_reversal", "source_id": legacy_number})
    )


def _has_folio_posting_for_charge(folio: dict[str, Any], charge_id: Any) -> bool:
    charge_key = _source_id(charge_id)
    for posting in folio.get("postings", []) or []:
        reference_id = posting.get("reference_id")
        if _source_id(reference_id) == charge_key:
            return True
    return False


def _active_stay_room_ids(db: Any, prop_id: int) -> set[str]:
    """hotel_room_ids physically occupied today by a checked-in stay.

    A room is genuinely occupied only while a booking with an active stay
    (``stay_status == "checked_in"``, or the legacy ``status == "checked_in"``)
    references it and today falls inside the stay window. Upcoming
    (confirmed/pending) reservations do not make a room physically occupied.
    """
    occupied: set[str] = set()
    today = datetime.now(timezone.utc).date()
    for booking in db.booking_orders.find(
        {
            "prop_id": prop_id,
            "$or": [{"stay_status": "checked_in"}, {"status": "checked_in"}],
        },
        {"assigned_rooms": 1, "check_in_date": 1, "check_out_date": 1},
    ):
        try:
            check_in = date.fromisoformat(str(booking.get("check_in_date", ""))[:10])
            check_out = date.fromisoformat(str(booking.get("check_out_date", ""))[:10])
        except (TypeError, ValueError):
            continue
        if not (check_in <= today < check_out):
            continue
        for room in booking.get("assigned_rooms", []) or []:
            room_id = room.get("hotel_room_id") or room.get("room_id") if isinstance(room, dict) else room
            if room_id:
                occupied.add(str(room_id))
    return occupied


def find_phantom_occupied_rooms(db: Any, prop_id: int) -> list[dict[str, Any]]:
    """room_status_log rows marked occupied_clean with no active stay.

    Rows without a ``hotel_room_id`` cannot be matched to any stay, so they
    are never guessed at — skipping them keeps the rule conservative.
    """
    occupied_ids = _active_stay_room_ids(db, prop_id)
    phantom: list[dict[str, Any]] = []
    for doc in db.room_status_log.find(
        {"prop_id": prop_id, "status": "occupied_clean"},
        {"room_label": 1, "hotel_room_id": 1, "note": 1, "status": 1},
    ):
        room_id = doc.get("hotel_room_id")
        if not room_id or str(room_id) in occupied_ids:
            continue
        phantom.append(doc)
    return phantom


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
        {"booking_id": 1, "invoice_id": 1, "amount": 1, "status": 1, "method": 1, "reference": 1, "refund_id": 1, "reconciliation_status": 1, "reconciliation_reason": 1, "_id": 1},
    ).sort("_id", 1):
        invoice_ref = payment.get("invoice_id")
        referenced_invoice = None
        if invoice_ref not in (None, ""):
            referenced_invoice = db.reservation_invoices.find_one(
                {"prop_id": prop_id, "$or": [{"_id": invoice_ref}, {"invoice_number": invoice_ref}]},
                {"_id": 1},
            )
        status = str(payment.get("status") or "unknown").lower()
        if status == "refunded":
            refund_event_id = str(payment.get("refund_id") or payment.get("reference") or payment.get("_id"))
            has_refund_document = db.refund_documents.find_one({
                "payment_id": payment.get("_id"),
                "status": "issued",
                "accounting_status": "posted",
            }, {"_id": 1}) is not None
            has_refund_ledger = _balanced_source_rows(
                db,
                {"prop_id": prop_id, "source": "payment_refund", "source_id": refund_event_id},
            )
            has_explicit_unapplied_state = (
                invoice_ref in (None, "")
                and payment.get("reconciliation_status") == "unapplied_refund"
            )
            if has_refund_document and has_refund_ledger and (invoice_ref not in (None, "") or has_explicit_unapplied_state):
                continue
            findings.append(_finding(
                domain="payment",
                severity="warning",
                source_ids=[payment.get("_id"), payment.get("booking_id")],
                expected={"refund_document": "issued", "refund_ledger": "balanced"},
                actual={
                    "status": payment.get("status"),
                    "invoice_id": invoice_ref,
                    "refund_id": payment.get("refund_id"),
                    "refund_document": has_refund_document,
                    "refund_ledger": has_refund_ledger,
                    "reconciliation_status": payment.get("reconciliation_status"),
                },
                repair_policy="idempotent_migration",
                message="Pago reembolsado sin documento de reembolso o reversa contable completa.",
            ))
            continue
        if invoice_ref not in (None, "") and referenced_invoice is not None:
            continue
        severity = "info" if status in {"failed", "rejected", "declined", "error"} else "warning"
        findings.append(_finding(
            domain="payment",
            severity=severity,
            source_ids=[payment.get("_id"), payment.get("booking_id")],
            expected={"invoice_id": "present_for_confirmed_or_refunded_payment"},
            actual={
                "invoice_id": invoice_ref,
                "status": payment.get("status"),
                "reconciliation_status": payment.get("reconciliation_status"),
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
        {"invoice_number": 1, "total": 1, "status": 1, "source": 1, "folio_id": 1, "booking_id": 1, "supersedes_invoice_id": 1, "recognized_total": 1, "accounting_status": 1, "_id": 1},
    ).sort("_id", 1):
        invoice_number = invoice.get("invoice_number")
        invoice_status = str(invoice.get("status") or "").lower()
        if _historical_invoice_has_evidence(db, prop_id, invoice):
            continue
        if invoice_status in {"cancelled", "refunded"}:
            reversal_rows = list(db.ledger_transactions.find(
                {"prop_id": prop_id, "source": "invoice_reversal", "source_id": invoice.get("invoice_number")},
                {"debit": 1, "credit": 1},
            ))
            reversal_debit = round(sum(_amount(row.get("debit")) for row in reversal_rows), 2)
            reversal_credit = round(sum(_amount(row.get("credit")) for row in reversal_rows), 2)
            is_reconciled_void = (
                invoice.get("accounting_status") == "reversed"
                and _amount(invoice.get("recognized_total")) == 0.0
                and reversal_debit == _amount(invoice.get("total"))
                and reversal_credit == _amount(invoice.get("total"))
            )
            if is_reconciled_void:
                continue
            findings.append(_finding(
                domain="invoice",
                severity="warning",
                source_ids=[invoice.get("_id"), invoice_number],
                expected={"ledger_repair": "manual_reversal_or_void_review"},
                actual={"status": invoice_status, "invoice_total": _amount(invoice.get("total"))},
                repair_policy="manual",
                message=(
                    "Factura cancelada con importe positivo; requiere revisión manual de anulación."
                    if invoice_status == "cancelled"
                    else "Factura reembolsada con importe positivo; requiere revisión manual del reverso."
                ),
            ))
            continue
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

    # Every source-bearing journal must resolve back to a business document.
    # A globally balanced ledger can still contain orphan or duplicated source
    # events, so inspect source identity independently of debit/credit totals.
    source_groups: dict[tuple[str, str], dict[str, Any]] = {}
    for row in db.ledger_transactions.find(
        {"prop_id": prop_id},
        {"source": 1, "source_id": 1, "journal_entry_id": 1},
    ):
        source = str(row.get("source") or "").strip()
        source_id = str(row.get("source_id") or "").strip()
        key = (source, source_id)
        group = source_groups.setdefault(key, {"journals": set(), "rows": 0})
        journal_id = row.get("journal_entry_id")
        if journal_id:
            group["journals"].add(str(journal_id))
        group["rows"] += 1

    for (source, source_id), group in sorted(source_groups.items()):
        if not source or not source_id:
            findings.append(_finding(
                domain="ledger",
                severity="warning",
                source_ids=[source or "missing-source", source_id or "missing-source-id"],
                expected={"source": "present", "source_id": "present"},
                actual={"source": source or None, "source_id": source_id or None, "rows": group["rows"]},
                repair_policy="manual",
                message="Asiento del libro mayor sin identidad de fuente completa.",
            ))
            continue

        if source == "invoice" and not db.reservation_invoices.find_one(
            {"prop_id": prop_id, "invoice_number": source_id},
            {"_id": 1},
        ):
            findings.append(_finding(
                domain="ledger",
                severity="critical",
                source_ids=[f"{source}:{source_id}"],
                expected={"source_document": "reservation_invoices.invoice_number"},
                actual={"source": source, "source_id": source_id, "journal_count": len(group["journals"])},
                repair_policy="manual",
                message="Asiento del libro mayor huérfano: no existe el documento de origen.",
            ))

        if len(group["journals"]) > 1:
            findings.append(_finding(
                domain="ledger",
                severity="warning",
                source_ids=[f"{source}:{source_id}"],
                expected={"journal_count": 1},
                actual={"journal_count": len(group["journals"]), "journal_entry_ids": sorted(group["journals"])},
                repair_policy="manual",
                message="El mismo source_id aparece repartido en varios journals; revisar posible duplicación.",
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
        {
            "booking_id": 1,
            "amount": 1,
            "description": 1,
            "posting_status": 1,
            "posting_error": 1,
            "_id": 1,
        },
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
                    "posting_status": charge.get("posting_status"),
                    "posting_error": charge.get("posting_error"),
                },
                repair_policy="manual",
                message="Cargo adicional sin posting trazable en el folio.",
            ))

    # Nightly reservation/calendar reconciliation. The inventory calendar is
    # an aggregate projection, so compare it to the reservation's assigned
    # physical rooms (or its requested room count when assignment is absent)
    # per room type and night. A balanced GL cannot reveal this operational
    # drift.
    for booking in db.booking_orders.find(
        {
            "prop_id": prop_id,
            "status": {"$in": ["confirmed", "checked_in"]},
            # ``status`` is the reservation workflow state and often remains
            # ``confirmed`` after the stay ends. Current nightly occupancy is
            # determined by ``stay_status``; checkout/no-show/cancelled stays
            # must not create findings against today's calendar projection.
            "stay_status": {"$nin": ["checked_out", "no_show", "cancelled"]},
        },
        {
            "booking_id": 1,
            "room_type_id": 1,
            "rooms": 1,
            "assigned_rooms": 1,
            "check_in_date": 1,
            "check_out_date": 1,
        },
    ).sort("booking_id", 1):
        try:
            check_in = date.fromisoformat(str(booking.get("check_in_date", ""))[:10])
            check_out = date.fromisoformat(str(booking.get("check_out_date", ""))[:10])
        except (TypeError, ValueError):
            continue
        if check_out <= check_in:
            continue

        assigned = booking.get("assigned_rooms") or []
        assigned_ids = [
            str(room.get("hotel_room_id") or room.get("room_id") or "")
            if isinstance(room, dict) else str(room)
            for room in assigned
        ]
        assigned_ids = [room_id for room_id in assigned_ids if room_id]
        expected_by_type: dict[str, int] = {}
        if assigned_ids:
            room_docs = list(db.hotel_rooms.find(
                {"prop_id": prop_id, "hotel_room_id": {"$in": assigned_ids}},
                {"hotel_room_id": 1, "room_type_id": 1},
            ))
            found_room_ids = {
                str(room.get("hotel_room_id"))
                for room in room_docs
                if room.get("hotel_room_id")
            }
            missing_room_ids = [room_id for room_id in assigned_ids if room_id not in found_room_ids]
            if missing_room_ids:
                findings.append(_finding(
                    domain="room",
                    severity="critical",
                    source_ids=[booking.get("booking_id"), *missing_room_ids],
                    expected={"assigned_rooms": "valid hotel_rooms.hotel_room_id references"},
                    actual={"missing_room_ids": missing_room_ids},
                    repair_policy="manual",
                    message="La reserva referencia habitaciones físicas inexistentes o de otro hotel.",
                ))
            for room in room_docs:
                room_type = str(room.get("room_type_id") or booking.get("room_type_id") or "")
                if room_type:
                    expected_by_type[room_type] = expected_by_type.get(room_type, 0) + 1
        # A booking without a physical assignment is allowed to reserve a room
        # type. Only use the requested room count as a fallback in that case;
        # never hide a stale assigned_rooms FK behind a synthetic inventory
        # expectation.
        if not assigned_ids and booking.get("room_type_id"):
            expected_by_type[str(booking["room_type_id"])] = max(1, int(booking.get("rooms", 1) or 1))
        if assigned_ids and not expected_by_type:
            continue

        for offset in range((check_out - check_in).days):
            night = (check_in + timedelta(days=offset)).isoformat()
            for room_type_id, expected_occupied in expected_by_type.items():
                calendar = db.room_inventory_calendar.find_one(
                    {
                        "prop_id": prop_id,
                        "room_type_id": room_type_id,
                        "date": night,
                        "is_deleted": {"$ne": True},
                    },
                    {"total_rooms": 1, "available_rooms": 1, "blocked_rooms": 1},
                )
                actual_occupied = None
                if calendar is not None:
                    actual_occupied = round(
                        float(calendar.get("total_rooms", 0) or 0)
                        - float(calendar.get("available_rooms", 0) or 0)
                        - float(calendar.get("blocked_rooms", 0) or 0),
                        2,
                    )
                if actual_occupied is not None and abs(actual_occupied - expected_occupied) < 0.01:
                    continue
                findings.append(_finding(
                    domain="inventory",
                    severity="warning",
                    source_ids=[booking.get("booking_id"), f"{room_type_id}:{night}"],
                    expected={
                        "occupied_rooms": expected_occupied,
                        "calendar": "present",
                    },
                    actual={
                        "date": night,
                        "room_type_id": room_type_id,
                        "occupied_rooms": actual_occupied,
                        "calendar": "present" if calendar is not None else "missing",
                    },
                    repair_policy="manual",
                    message="La disponibilidad nocturna no concilia con las habitaciones reservadas; requiere revisión.",
                ))

    # Physical room status must match reality. A room marked occupied_clean
    # with no checked-in stay referencing it is a phantom occupancy (the
    # auto-assignment flow wrote occupied_clean without a real check-in), and
    # it corrupts housekeeping metrics and blocks future check-ins.
    for status_doc in find_phantom_occupied_rooms(db, prop_id):
        findings.append(_finding(
            domain="room_status",
            severity="warning",
            source_ids=[status_doc.get("room_label"), status_doc.get("hotel_room_id")],
            expected={"status": "vacant_clean", "active_stay": True},
            actual={
                "status": status_doc.get("status"),
                "active_stay": False,
                "note": status_doc.get("note"),
            },
            repair_policy="idempotent_migration",
            message="Habitación marcada como ocupada sin estancia activa; requiere reversión a vacante.",
        ))

    # Current maintenance documents are operationally valid but financially
    # incomplete when they lack cost/invoice/ledger evidence.
    for task in db.maintenance_tasks.find(
        {"prop_id": prop_id, "status": {"$ne": "deleted"}},
        {"cost": 1, "actual_cost": 1, "expense_invoice_id": 1, "ledger_journal_id": 1, "financial_link_status": 1, "room_id": 1, "_id": 1},
    ).sort("_id", 1    ):
        if task.get("financial_link_status") == "no_cost_recorded":
            continue
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
