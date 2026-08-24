"""Consistencia del desglose de precios con el total final (factura).

Regresión: ``_build_price_breakdown`` (detalle de reserva) sumaba IVA (16%)
ENCIMA del total final — en el branch derivado (``total_price``) y en el de
calendario cuando el plan tiene IVA incluido. El huésped veía "Desglose de
precios → Total $218.08" mientras la factura y el resumen financiero decían
"Total $188.00".

Invariante: el ``total`` del desglose debe ser SIEMPRE igual al
``total_price`` de la reserva (el precio final), con subtotal/IVA como split
de presentación idéntico al de la factura (subtotal = total / 1.16).
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.app.modules.reservations.service.queries import get_booking_detail


def _seed_booking(db, booking_id: str, **overrides) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Pricing Guest",
        "guest_email": "pricing@test.com",
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


def _seed_calendar_rates(db, rate_amount: float = 94.0, rate_plan_id: str = "RP-1-advance") -> None:
    for d in ("2026-08-20", "2026-08-21"):
        db.hotel_rate_calendar.insert_one({
            "prop_id": 1,
            "date": d,
            "room_type_id": "RT-1-deluxe",
            "rate_plan_id": rate_plan_id,
            "rate_amount": rate_amount,
            "currency": "USD",
        })


def test_derived_breakdown_matches_booking_total_and_invoice_split(db):
    """Sin tarifas en el calendario, el desglose deriva de ``total_price`` SIN
    sumarle IVA encima: total == 188 == factura; subtotal/IVA == split 1.16."""
    booking_id = "BK-PRICE-DERIVED"
    _seed_booking(db, booking_id)

    detail = get_booking_detail(booking_id)

    assert detail is not None
    pb = detail["price_breakdown"]
    assert pb is not None
    assert pb["source"] == "derived"
    assert pb["total"] == 188.0
    assert pb["subtotal"] == 162.07
    assert pb["taxes"] == 25.93
    assert round(pb["subtotal"] + pb["taxes"], 2) == pb["total"]
    assert [n["rate"] for n in pb["nights"]] == [94.0, 94.0]


def test_calendar_breakdown_tax_included_plan_matches_invoice(db):
    """Plan con IVA incluido: las tarifas del calendario son brutas; el total
    no se toca (188) y el split es el mismo de la factura."""
    booking_id = "BK-PRICE-CAL-TAXIN"
    _seed_booking(db, booking_id)
    db.rate_plans.insert_one({
        "rate_plan_id": "RP-1-advance",
        "prop_id": 1,
        "base_rate": 94.0,
        "tax_included": True,
        "tax_rate": 16,
    })
    _seed_calendar_rates(db)

    detail = get_booking_detail(booking_id)

    assert detail is not None
    pb = detail["price_breakdown"]
    assert pb is not None
    assert pb["source"] == "calendar"
    assert pb["total"] == 188.0
    assert pb["subtotal"] == 162.07
    assert pb["taxes"] == 25.93
    assert round(pb["subtotal"] + pb["taxes"], 2) == pb["total"]


def test_calendar_breakdown_tax_not_included_adds_tax_and_keeps_invariant(db):
    """Plan sin IVA incluido y tasa 16%: el total del desglose debe coincidir
    con el total final de la reserva (218.08) — nunca un tercer número."""
    booking_id = "BK-PRICE-CAL-TAXOUT"
    _seed_booking(db, booking_id, total_price=218.08)
    db.rate_plans.insert_one({
        "rate_plan_id": "RP-1-advance",
        "prop_id": 1,
        "base_rate": 94.0,
        "tax_included": False,
        "tax_rate": 16,
    })
    _seed_calendar_rates(db)

    detail = get_booking_detail(booking_id)

    assert detail is not None
    pb = detail["price_breakdown"]
    assert pb is not None
    assert pb["source"] == "calendar"
    assert pb["total"] == 218.08
    assert pb["subtotal"] == 188.0
    assert pb["taxes"] == 30.08
    assert round(pb["subtotal"] + pb["taxes"], 2) == pb["total"]
