"""Audit report — post-backfill consistency of booking↔folio↔invoice.

Spec: ``scripts/audit_backfill_consistency.py`` produce un reporte que lista
cada reserva con su folio y factura, y detecta inconsistencias restantes
tras el backfill de precios:

- ``folio_room_zero`` — folio cuyo posting de habitación quedó en $0 pero la
  reserva tiene ``total_price > 0`` (estado roto que el backfill de folios
  solo corrige cuando backfillea la reserva en la misma corrida; el caso
  ``FL-202607-0003`` de la demo es una reserva YA con precio).
- ``invoice_zero`` — factura con ``total == 0``/ausente y reserva con precio.
- ``due_invoice_mismatch`` — folio ``total_due`` vs ``invoice.total`` difieren
  en más de un umbral (1.00) cuando ambos documentos existen y tienen montos
  reales. Señala divergencia entre la cuenta viva y la factura emitida.
- ``folio_expired_open`` — folio ``status=open`` cuyo ``check_out_date`` ya
  pasó (el cleanup automático no lo cerró).
- ``orphan_folio`` / ``orphan_invoice`` — documento que referencia un
  ``booking_id`` inexistente.
- ``missing_folio`` / ``missing_invoice`` — reserva operativa (no
  cancelled/rejected) sin folio o sin factura. Informativo, no es un error.

El script expone ``audit_consistency(db, *, today=None) -> dict`` (testeable)
y un ``main()`` que imprime el reporte en consola. Es SOLO lectura — nunca
escribe.
"""
from __future__ import annotations

import pytest
from bson import ObjectId

from scripts.audit_backfill_consistency import audit_consistency

pytestmark = pytest.mark.asyncio


def _seed_booking(db, booking_id: str, **overrides) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": 9001,
        "status": "confirmed",
        "check_in_date": "2026-08-01",
        "check_out_date": "2026-08-04",
        "total_nights": 3,
        "total_price": 360.0,
        "currency": "USD",
        "is_test": True,
    }
    doc.update(overrides)
    db.booking_orders.insert_one(doc)


def _seed_folio(db, booking_id: str, **overrides) -> None:
    from datetime import datetime, timezone

    from bson import ObjectId

    doc = {
        "folio_number": f"FL-AUD-{booking_id[-4:]}",
        "booking_id": booking_id,
        "prop_id": 9001,
        "status": "open",
        "check_out_date": "2026-08-04",
        "total_room": 360.0,
        "total_charges": 0.0,
        "total_discounts": 0.0,
        "total_payments": 0.0,
        "total_due": 360.0,
        "postings": [
            {
                "posting_id": ObjectId(),
                "type": "room",
                "category": "Habitación",
                "concept": "Habitación — 3 noche(s)",
                "amount": 360.0,
                "quantity": 3,
                "unit_price": 120.0,
                "reference_id": booking_id,
                "reference_type": "booking",
                "posted_at": datetime.now(timezone.utc),
            }
        ],
        "posting_count": 1,
        "invoice_id": None,
    }
    doc.update(overrides)
    db.guest_folios.insert_one(doc)


def _seed_invoice(db, booking_id: str, **overrides) -> None:
    doc = {
        "invoice_number": f"INV-AUD-{booking_id[-4:]}",
        "booking_id": booking_id,
        "prop_id": 9001,
        "room_subtotal": 310.34,
        "extras_total": 0.0,
        "subtotal": 310.34,
        "taxes": 49.66,
        "total": 360.0,
        "status": "issued",
        "line_items": [],
    }
    doc.update(overrides)
    db.reservation_invoices.insert_one(doc)


def _by_category(report: dict, category: str) -> list:
    return [i for i in report["issues"] if i["category"] == category]


async def test_audit_detects_folio_room_zero_with_priced_booking(db):
    """Folio con posting de habitación en $0 y reserva con precio → folio_room_zero."""
    _seed_booking(db, "BK-AUD-0001")
    _seed_folio(db, "BK-AUD-0001", total_room=0.0, total_due=0.0, postings=[
        {"posting_id": ObjectId(), "type": "room",
         "category": "Habitación", "concept": "Habitación", "amount": 0.0,
         "quantity": 3, "unit_price": 0.0, "reference_id": "BK-AUD-0001",
         "reference_type": "booking"}
    ])

    report = audit_consistency(db, today="2026-08-10")
    hits = _by_category(report, "folio_room_zero")
    assert len(hits) == 1
    assert hits[0]["booking_id"] == "BK-AUD-0001"
    assert hits[0]["total_room"] == 0.0
    assert hits[0]["booking_total"] == 360.0


async def test_audit_detects_invoice_zero_with_priced_booking(db):
    """Factura en $0 con reserva con precio → invoice_zero."""
    _seed_booking(db, "BK-AUD-0002")
    _seed_invoice(db, "BK-AUD-0002", subtotal=0.0, taxes=0.0, total=0.0)

    report = audit_consistency(db, today="2026-08-10")
    hits = _by_category(report, "invoice_zero")
    assert len(hits) == 1
    assert hits[0]["booking_id"] == "BK-AUD-0002"


async def test_audit_detects_due_invoice_mismatch(db):
    """Folio total_due divergente de invoice.total → due_invoice_mismatch."""
    _seed_booking(db, "BK-AUD-0003")
    _seed_folio(db, "BK-AUD-0003", total_charges=283.0, total_due=283.0)
    _seed_invoice(db, "BK-AUD-0003", subtotal=80.0, taxes=12.8, total=92.8)

    report = audit_consistency(db, today="2026-08-10")
    hits = _by_category(report, "due_invoice_mismatch")
    assert len(hits) == 1
    assert hits[0]["booking_id"] == "BK-AUD-0003"
    assert hits[0]["folio_due"] == 283.0
    assert hits[0]["invoice_total"] == 92.8
    assert abs(hits[0]["diff"]) > 1.0


async def test_audit_detects_due_invoice_mismatch_on_closed_folio(db):
    """Folio CERRADO con deuda pendiente vs factura pagada también diverge.

    Caso demo real: FL-202607-0003 se cerró con total_due=283 pero su
    factura (paid) es de 92.80 — el folio acumuló cargos que la factura no
    refleja. Un folio cerrado correctamente liquidado tiene total_due=0;
    uno cerrado con deuda pendiente Y factura divergente es inconsistencia.
    """
    _seed_booking(db, "BK-AUD-0031")
    _seed_folio(db, "BK-AUD-0031", status="closed", total_charges=283.0, total_due=283.0)
    _seed_invoice(db, "BK-AUD-0031", subtotal=80.0, taxes=12.8, total=92.8, status="paid")

    report = audit_consistency(db, today="2026-08-10")
    hits = _by_category(report, "due_invoice_mismatch")
    assert len(hits) == 1
    assert hits[0]["booking_id"] == "BK-AUD-0031"
    assert abs(hits[0]["diff"] - 190.2) < 0.01


async def test_audit_closed_settled_folio_no_mismatch(db):
    """Folio cerrado liquidado (total_due=0) no se marca aunque haya factura."""
    _seed_booking(db, "BK-AUD-0032")
    _seed_folio(db, "BK-AUD-0032", status="closed", total_payments=360.0, total_due=0.0)
    _seed_invoice(db, "BK-AUD-0032", status="paid")

    report = audit_consistency(db, today="2026-08-10")
    assert _by_category(report, "due_invoice_mismatch") == []


async def test_audit_consistent_pair_has_no_mismatch(db):
    """Folio y factura coherentes → sin mismatches ni folio_room_zero."""
    _seed_booking(db, "BK-AUD-0004")
    _seed_folio(db, "BK-AUD-0004")
    _seed_invoice(db, "BK-AUD-0004")

    report = audit_consistency(db, today="2026-08-10")
    assert _by_category(report, "due_invoice_mismatch") == []
    assert _by_category(report, "folio_room_zero") == []
    assert _by_category(report, "invoice_zero") == []


async def test_audit_detects_expired_open_folio(db):
    """Folio abierto cuyo check_out ya pasó → folio_expired_open."""
    _seed_booking(db, "BK-AUD-0005", check_out_date="2026-07-30")
    _seed_folio(db, "BK-AUD-0005", check_out_date="2026-07-30")

    report = audit_consistency(db, today="2026-08-10")
    hits = _by_category(report, "folio_expired_open")
    assert len(hits) == 1
    assert hits[0]["booking_id"] == "BK-AUD-0005"
    assert hits[0]["check_out_date"] == "2026-07-30"


async def test_audit_closed_folio_not_flagged_as_expired(db):
    """Folio cerrado vencido no se marca (ya se liquidó)."""
    _seed_booking(db, "BK-AUD-0006", check_out_date="2026-07-30")
    _seed_folio(db, "BK-AUD-0006", check_out_date="2026-07-30", status="closed")

    report = audit_consistency(db, today="2026-08-10")
    assert _by_category(report, "folio_expired_open") == []


async def test_audit_detects_orphan_folio_and_invoice(db):
    """Documentos que referencian un booking inexistente → orphan."""
    _seed_folio(db, "BK-NO-EXISTE", folio_number="FL-ORPHAN-1")
    _seed_invoice(db, "BK-NO-EXISTE", invoice_number="INV-ORPHAN-1")

    report = audit_consistency(db, today="2026-08-10")
    assert len(_by_category(report, "orphan_folio")) == 1
    assert len(_by_category(report, "orphan_invoice")) == 1


async def test_audit_missing_folio_is_informative(db):
    """Reserva operativa sin folio → missing_folio (informativo)."""
    _seed_booking(db, "BK-AUD-0007")
    _seed_invoice(db, "BK-AUD-0007")

    report = audit_consistency(db, today="2026-08-10")
    hits = _by_category(report, "missing_folio")
    assert len(hits) == 1
    assert hits[0]["booking_id"] == "BK-AUD-0007"


async def test_audit_skips_cancelled_rejected_for_missing(db):
    """Reservas canceladas/rechazadas no generan missing_folio/invoice."""
    _seed_booking(db, "BK-AUD-0008", status="cancelled")
    _seed_booking(db, "BK-AUD-0009", status="rejected")

    report = audit_consistency(db, today="2026-08-10")
    assert _by_category(report, "missing_folio") == []
    assert _by_category(report, "missing_invoice") == []


async def test_audit_bookings_summary_lists_each_booking(db):
    """El reporte incluye la tabla booking↔folio↔invoice (cross-reference)."""
    _seed_booking(db, "BK-AUD-0041")
    _seed_folio(db, "BK-AUD-0041")
    _seed_invoice(db, "BK-AUD-0041")
    _seed_booking(db, "BK-AUD-0042")  # sin folio ni factura

    report = audit_consistency(db, today="2026-08-10")
    summary = report["bookings_summary"]
    assert len(summary) == 2
    by_id = {s["booking_id"]: s for s in summary}

    ok = by_id["BK-AUD-0041"]
    assert ok["folio_number"] == "FL-AUD-0041"
    assert ok["invoice_number"] == "INV-AUD-0041"
    assert ok["folio_due"] == 360.0
    assert ok["invoice_total"] == 360.0
    assert ok["consistent"] is True

    none_doc = by_id["BK-AUD-0042"]
    assert none_doc["folio_number"] is None
    assert none_doc["invoice_number"] is None
    assert none_doc["consistent"] is False


async def test_audit_report_shapes(db):
    """El reporte incluye counts y total_bookings consistentes."""
    _seed_booking(db, "BK-AUD-0010")
    _seed_folio(
        db, "BK-AUD-0010", total_room=0.0, total_due=0.0,
        postings=[
            {"posting_id": ObjectId(), "type": "room",
             "category": "Habitación", "concept": "Habitación", "amount": 0.0,
             "quantity": 3, "unit_price": 0.0, "reference_id": "BK-AUD-0010",
             "reference_type": "booking"}
        ],
    )

    report = audit_consistency(db, today="2026-08-10")
    assert report["total_bookings"] == 1
    assert "counts" in report
    assert report["counts"].get("folio_room_zero", 0) == 1
    assert report["counts"].get("due_invoice_mismatch", 0) == 0
    assert sum(report["counts"].values()) == len(report["issues"])
