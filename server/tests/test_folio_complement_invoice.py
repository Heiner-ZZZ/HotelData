"""Complemento fiscal de postings de folio NO cubiertos por la factura principal.

Decisión de negocio (B): la factura final se realinea CONTRA EL FOLIO al
cierre del checkout. Los postings de extensión (``extend_stay``), salida
anticipada (``early_checkout_penalty``) y late check-out (``late_checkout``)
viven en el folio pero NO en la factura principal → se emite una factura
complementaria (charges-only) cuyo TOTAL es EXACTO al posting del folio
(misma convención tax-incluida que la factura principal: subtotal = total/1.16)
— nunca un tercer número (regresión: noches extra/penalizaciones invisibles en
la factura del huésped).
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.app.modules.billing.service.lifecycle.invoices import create_folio_postings_complement_invoice


def _seed_booking(db, booking_id: str, **overrides) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Folio Complement Guest",
        "guest_email": "folio@test.com",
        "room_type_id": "RT-1-deluxe",
        "rate_plan_id": "RP-1-advance",
        "check_in_date": "2026-08-20",
        "check_out_date": "2026-08-22",
        "rooms": 1,
        "total_nights": 2,
        "total_price": 188.0,
        "currency": "USD",
        "status": "confirmed",
        "created_at": datetime.now(timezone.utc),
        "is_test": True,
    }
    doc.update(overrides)
    db.booking_orders.insert_one(doc)


def _seed_main_invoice(db, booking_id: str, **overrides) -> str:
    doc = {
        "invoice_number": "INV-FOLIO-0001",
        "booking_id": booking_id,
        "prop_id": 1,
        "subtotal": 162.07,
        "room_subtotal": 162.07,
        "extras_total": 0.0,
        "taxes": 25.93,
        "total": 188.0,
        "status": "issued",
        "line_items": [],
        "issued_at": datetime.now(timezone.utc),
    }
    doc.update(overrides)
    return str(db.reservation_invoices.insert_one(doc).inserted_id)


def _seed_folio(db, booking_id: str, postings: list[dict]) -> None:
    db.guest_folios.insert_one({
        "folio_number": f"FL-{booking_id}",
        "booking_id": booking_id,
        "prop_id": 1,
        "status": "open",
        "postings": postings,
        "total_room": 188.0,
        "total_charges": round(sum(float(p.get("amount", 0) or 0) for p in postings), 2),
        "total_due": round(sum(float(p.get("amount", 0) or 0) for p in postings), 2),
        "created_at": datetime.now(timezone.utc),
    })


def _posting(reference_type: str, amount: float, concept: str = "") -> dict:
    return {
        "posting_id": "p",
        "type": "charge",
        "category": "Habitación",
        "concept": concept or reference_type,
        "amount": amount,
        "quantity": 1,
        "unit_price": amount,
        "reference_type": reference_type,
    }


def test_extend_stay_posting_complemented_at_exact_total(db):
    """Noches extra de extensión: la complementaria totaliza el posting (94),
    no 94+IVA encima ni un tercer número."""
    booking_id = "BK-FOLIO-EXTEND"
    _seed_booking(db, booking_id)
    main_id = _seed_main_invoice(db, booking_id)
    _seed_folio(db, booking_id, [
        _posting("booking", 188.0, "Habitación 2 noches"),
        _posting("extend_stay", 94.0, "Extensión de estancia — 1 noche adicional"),
    ])

    inv = create_folio_postings_complement_invoice(booking_id, changed_by="checkout")

    assert inv is not None
    assert inv["split_type"] == "charges_only"
    assert inv["complement_type"] == "folio_postings"
    assert inv["parent_invoice_id"] == main_id
    assert inv["total"] == 94.0
    assert inv["subtotal"] == 81.03
    assert inv["taxes"] == 12.97
    assert round(inv["subtotal"] + inv["taxes"], 2) == inv["total"]
    assert any(
        item.get("reference_type") == "extend_stay"
        for item in (inv.get("line_items") or [])
    )


def test_early_checkout_penalty_complemented(db):
    booking_id = "BK-FOLIO-EARLY"
    _seed_booking(db, booking_id)
    _seed_main_invoice(db, booking_id)
    _seed_folio(db, booking_id, [
        _posting("booking", 188.0),
        _posting("early_checkout_penalty", 47.94, "Salida anticipada — Penalización del 51%"),
    ])

    inv = create_folio_postings_complement_invoice(booking_id, changed_by="early_checkout")

    assert inv is not None
    assert inv["total"] == 47.94
    assert any(
        item.get("reference_type") == "early_checkout_penalty"
        for item in (inv.get("line_items") or [])
    )


def test_late_checkout_fee_complemented(db):
    booking_id = "BK-FOLIO-LATE"
    _seed_booking(db, booking_id)
    _seed_main_invoice(db, booking_id)
    _seed_folio(db, booking_id, [
        _posting("booking", 188.0),
        _posting("late_checkout", 20.0, "Late check-out autorizado — 120 min"),
    ])

    inv = create_folio_postings_complement_invoice(booking_id, changed_by="checkout")

    assert inv is not None
    assert inv["total"] == 20.0
    assert inv["subtotal"] == 17.24
    assert inv["taxes"] == 2.76


def test_idempotent_with_same_snapshot(db):
    """Misma snapshot de postings → se devuelve la misma complementaria."""
    booking_id = "BK-FOLIO-IDEM"
    _seed_booking(db, booking_id)
    _seed_main_invoice(db, booking_id)
    _seed_folio(db, booking_id, [
        _posting("booking", 188.0),
        _posting("extend_stay", 94.0),
    ])

    first = create_folio_postings_complement_invoice(booking_id)
    second = create_folio_postings_complement_invoice(booking_id)

    assert first is not None and second is not None
    assert second["invoice_number"] == first["invoice_number"]
    assert db.reservation_invoices.count_documents({"booking_id": booking_id, "split_type": "charges_only"}) == 1


def test_snapshot_change_rebuilds_in_place_before_payment(db):
    """Si la snapshot cambió antes del pago, la complementaria se reconstruye
    en el lugar (extend_stay + early_checkout_penalty) sin duplicar."""
    booking_id = "BK-FOLIO-REBUILD"
    _seed_booking(db, booking_id)
    _seed_main_invoice(db, booking_id)
    _seed_folio(db, booking_id, [
        _posting("booking", 188.0),
        _posting("extend_stay", 94.0),
    ])

    first = create_folio_postings_complement_invoice(booking_id)
    assert first["total"] == 94.0

    # El huésped además hace early check-out → nuevo posting en el folio.
    db.guest_folios.update_one(
        {"booking_id": booking_id},
        {"$push": {"postings": _posting("early_checkout_penalty", 47.94)}},
    )
    second = create_folio_postings_complement_invoice(booking_id)

    assert second["invoice_number"] == first["invoice_number"]
    assert second["total"] == 141.94
    assert db.reservation_invoices.count_documents({"booking_id": booking_id, "split_type": "charges_only"}) == 1


def test_no_gap_returns_none(db):
    """Folio sin postings elegibles (solo la estadía) → sin complementaria."""
    booking_id = "BK-FOLIO-NOGAP"
    _seed_booking(db, booking_id)
    _seed_main_invoice(db, booking_id)
    _seed_folio(db, booking_id, [_posting("booking", 188.0)])

    assert create_folio_postings_complement_invoice(booking_id) is None


def test_missing_folio_or_main_invoice_returns_none(db):
    booking_id = "BK-FOLIO-NONE"
    _seed_booking(db, booking_id)
    assert create_folio_postings_complement_invoice(booking_id) is None

    _seed_main_invoice(db, booking_id)
    assert create_folio_postings_complement_invoice(booking_id) is None
