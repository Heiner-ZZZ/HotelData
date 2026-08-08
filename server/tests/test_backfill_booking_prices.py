"""Migration backfill — bookings created without a price.

Spec: las reservas creadas mientras ``hotel_rate_calendar`` no cubría sus
fechas quedaron con ``total_price=None``. El script
``scripts/migrate_backfill_booking_prices.py`` las recalcula con el path
canónico ``_calculate_total_price`` (que ahora cae a ``rate_plans.base_rate``)
y ``$set`` del precio + campos de tax + metadata de migración.

También recalcula los folios (``guest_folios``) de esas reservas cuyo posting
de habitación quedó en $0: mirror de ``folio.create_folio``
(total_room = total, posting amount/unit_price/quantity con el precio nuevo,
total_due = total_room + total_charges − total_discounts − total_payments).

Reglas:
- Idempotente: re-correr no duplica ni re-toca reservas ya con precio.
- ``--dry-run``: reporta sin escribir.
- Reservas sin tarifa calculable (ni calendario ni rate plans) se saltan.
- Folios sin posting de habitación (p. ej. penalización de no-show) no se tocan.
- Nunca ``delete_many``; solo ``$set``.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from scripts.migrate_backfill_booking_prices import backfill_booking_prices

pytestmark = pytest.mark.asyncio


def _seed(db, booking_id: str, **overrides) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": 9001,
        "status": "confirmed",
        "room_type_id": "RT-9001-doble",
        "rate_plan_id": "",
        "check_in_date": "2026-08-10",
        "check_out_date": "2026-08-13",
        "rooms": 1,
        "adults": 2,
        "children": 0,
        "total_nights": 3,
        "currency": "USD",
        "total_price": None,
        "original_total_price": None,
        "is_test": True,
    }
    doc.update(overrides)
    db.booking_orders.insert_one(doc)


def _seed_invoice(db, booking_id: str, **overrides) -> None:
    # En producción ``_write_both`` crea la factura y su mirror
    # ``fact_reservation_invoices`` con el MISMO _id — el test simula ese
    # estado (update_with_outbox hace update sin upsert sobre el mirror).
    doc = {
        "invoice_number": "INV-TEST-0001",
        "booking_id": booking_id,
        "prop_id": 9001,
        "room_subtotal": 0.0,
        "extras_total": 0.0,
        "subtotal": 0.0,
        "taxes": 0.0,
        "total": 0.0,
        "status": "issued",
        "line_items": [],
        "issued_at": datetime.now(timezone.utc),
    }
    doc.update(overrides)
    inserted = db.reservation_invoices.insert_one(doc)
    db.fact_reservation_invoices.insert_one({**doc, "_id": inserted.inserted_id})


def _seed_folio(db, booking_id: str, **overrides) -> None:
    doc = {
        "folio_number": "FL-TEST-0001",
        "booking_id": booking_id,
        "prop_id": 9001,
        "status": "open",
        "total_room": 0.0,
        "total_charges": 0.0,
        "total_discounts": 0.0,
        "total_payments": 0.0,
        "total_due": 0.0,
        "postings": [
            {
                "posting_id": ObjectId(),
                "type": "room",
                "category": "Habitación",
                "concept": "Habitación — 3 noche(s)",
                "amount": 0.0,
                "quantity": 3,
                "unit_price": 0.0,
                "reference_id": booking_id,
                "reference_type": "booking",
                "posted_at": datetime.now(timezone.utc),
            }
        ],
        "posting_count": 1,
    }
    doc.update(overrides)
    db.guest_folios.insert_one(doc)


async def test_backfill_recomputes_price_and_is_idempotent(db):
    """Recalcula con el path canónico (fallback a base_rate) y es idempotente."""
    db.rate_plans.insert_one({"prop_id": 9001, "rate_plan_id": "RP-9001-flex", "base_rate": 120.0})
    _seed(db, "BK-BF-0001")
    _seed(db, "BK-BF-0002", total_price=300.0)  # ya tiene precio → no se toca

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1

    doc = db.booking_orders.find_one({"booking_id": "BK-BF-0001"})
    assert doc["total_price"] == 360.0  # 3 noches × $120
    assert doc["metadata"]["migration_id"] == "backfill_booking_prices_v1"
    assert doc["pricing_backfilled_at"] is not None

    # Idempotente: la segunda corrida no re-toca nada.
    second = backfill_booking_prices(db)
    assert second["backfilled"] == 0
    assert second["scanned"] == 0  # ya no hay reservas sin precio


async def test_backfill_dry_run_does_not_write(db):
    """--dry-run reporta el impacto pero no escribe."""
    db.rate_plans.insert_one({"prop_id": 9002, "rate_plan_id": "RP-9002-flex", "base_rate": 100.0})
    _seed(db, "BK-BF-0003", prop_id=9002)

    result = backfill_booking_prices(db, dry_run=True)
    assert result["backfilled"] == 1
    doc = db.booking_orders.find_one({"booking_id": "BK-BF-0003"})
    assert doc["total_price"] is None  # no escrito
    assert doc.get("pricing_backfilled_at") is None


async def test_backfill_skips_unpricable_bookings(db):
    """Sin calendario ni rate plans → sin precio calculable → se salta."""
    _seed(db, "BK-BF-0004", prop_id=99999)
    result = backfill_booking_prices(db)
    assert result["backfilled"] == 0
    assert result["skipped_unpriced"] == 1
    doc = db.booking_orders.find_one({"booking_id": "BK-BF-0004"})
    assert doc["total_price"] is None


async def test_backfill_applies_discount_percent(db):
    """Respeta el descuento original de la reserva (mirror de create_booking)."""
    db.rate_plans.insert_one({"prop_id": 9003, "rate_plan_id": "RP-9003-flex", "base_rate": 200.0})
    _seed(db, "BK-BF-0005", prop_id=9003, discount_percent=10)
    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1
    doc = db.booking_orders.find_one({"booking_id": "BK-BF-0005"})
    # 3 noches × $200 = 600 → 10% off = 540
    assert doc["total_price"] == 540.0
    assert doc["original_total_price"] == 600.0


async def test_backfill_recomputes_no_show_penalty(db):
    """La penalización de no-show se recalcula con el precio backfilleado.

    Mirror de ``no_show.process_no_show``: rate_per_night = total/noches,
    penalty = rate_per_night × no_show_penalty_percent / 100 (el % ya quedó
    guardado en la reserva al procesar el no-show).
    """
    db.rate_plans.insert_one({"prop_id": 9004, "rate_plan_id": "RP-9004-flex", "base_rate": 120.0})
    _seed(
        db, "BK-BF-0006", prop_id=9004,
        status="confirmed", stay_status="no_show",
        no_show_penalty_amount=0.0, no_show_penalty_percent=100,
    )

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1
    doc = db.booking_orders.find_one({"booking_id": "BK-BF-0006"})
    assert doc["total_price"] == 360.0  # 3 noches × $120
    # rate_per_night = 360/3 = 120 → 100% → $120
    assert doc["no_show_penalty_amount"] == 120.0


async def test_backfill_recomputes_cancellation_penalty(db):
    """La penalización de cancelación se recalcula si ya se había cobrado.

    Solo se toca cuando ``cancellation_free`` es False (el flujo ya decidió
    que la cancelación estaba dentro de la ventana de penalización). El %
    guardado es el que el flujo usó realmente.
    """
    db.rate_plans.insert_one({"prop_id": 9005, "rate_plan_id": "RP-9005-flex", "base_rate": 200.0})
    _seed(
        db, "BK-BF-0007", prop_id=9005,
        status="cancelled",
        cancellation_free=False, cancellation_penalty_percent=50,
        cancellation_penalty_amount=0.0,
    )

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1
    doc = db.booking_orders.find_one({"booking_id": "BK-BF-0007"})
    assert doc["total_price"] == 600.0  # 3 noches × $200
    # one_night = 600/3 = 200 → 50% → $100
    assert doc["cancellation_penalty_amount"] == 100.0


async def test_backfill_keeps_free_cancellation_penalty_zero(db):
    """Cancelación fuera de la ventana (cancellation_free=True) no se toca."""
    db.rate_plans.insert_one({"prop_id": 9006, "rate_plan_id": "RP-9006-flex", "base_rate": 200.0})
    _seed(
        db, "BK-BF-0008", prop_id=9006,
        status="cancelled",
        cancellation_free=True, cancellation_penalty_percent=0,
        cancellation_penalty_amount=0.0,
    )

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1
    doc = db.booking_orders.find_one({"booking_id": "BK-BF-0008"})
    assert doc["total_price"] == 600.0
    assert doc["cancellation_penalty_amount"] == 0.0  # intacta


async def test_backfill_no_show_absent_percent_resolves_from_policy(db):
    """No-show sin no_show_penalty_percent guardado → resolver la política.

    Reservas de no-show procesadas antes de que el flujo guardara el %
    (legacy) no tienen el campo: el backfill lo resuelve con
    ``resolve_penalty_percent`` (misma jerarquía que process_no_show).
    """
    db.rate_plans.insert_one({"prop_id": 9007, "rate_plan_id": "RP-9007-flex", "base_rate": 120.0})
    db.hotel_policies.insert_one({
        "prop_id": 9007, "room_type_id": "", "rate_plan_id": "",
        "cancellation_penalty_percent": 50,
    })
    _seed(
        db, "BK-BF-0009", prop_id=9007,
        status="confirmed", stay_status="no_show",
        no_show_penalty_amount=0.0,  # sin no_show_penalty_percent (legacy)
    )

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1
    doc = db.booking_orders.find_one({"booking_id": "BK-BF-0009"})
    assert doc["total_price"] == 360.0
    # rate_per_night = 120 → 50% → $60 (percent resuelto y sellado)
    assert doc["no_show_penalty_amount"] == 60.0
    assert doc["no_show_penalty_percent"] == 50


async def test_backfill_keeps_stored_zero_no_show_percent(db):
    """no_show_penalty_percent=0 guardado significa 'sin penalización' — no se resuelve.

    ``process_no_show`` SIEMPRE guarda el percent; un 0 guardado es la
    política real del hotel (0%), no un campo ausente. El backfill no debe
    re-resolverlo a 100 y cobrar una noche completa retroactivamente.
    """
    db.rate_plans.insert_one({"prop_id": 9008, "rate_plan_id": "RP-9008-flex", "base_rate": 120.0})
    _seed(
        db, "BK-BF-0010", prop_id=9008,
        status="confirmed", stay_status="no_show",
        no_show_penalty_amount=0.0, no_show_penalty_percent=0,
    )

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1
    doc = db.booking_orders.find_one({"booking_id": "BK-BF-0010"})
    assert doc["total_price"] == 360.0
    assert doc["no_show_penalty_amount"] == 0.0  # política 0% → intacta
    assert doc["no_show_penalty_percent"] == 0


async def test_backfill_recomputes_folio_room_and_due(db):
    """El folio de una reserva backfilleada se recalcula (mirror de create_folio).

    Posting de habitación en $0 → total $360 (3 noches × $120); con cargos
    $5 y pagos $2, total_due = 360 + 5 − 2 = 363.
    """
    db.rate_plans.insert_one({"prop_id": 9009, "rate_plan_id": "RP-9009-flex", "base_rate": 120.0})
    _seed(db, "BK-BF-0011", prop_id=9009)
    _seed_folio(db, "BK-BF-0011", prop_id=9009, total_charges=5.0, total_payments=2.0, total_due=3.0)

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1
    assert result["folios_recomputed"] == 1

    folio = db.guest_folios.find_one({"booking_id": "BK-BF-0011"})
    assert folio["total_room"] == 360.0
    assert folio["total_due"] == 363.0
    room = next(p for p in folio["postings"] if p["type"] == "room")
    assert room["amount"] == 360.0
    assert room["unit_price"] == 120.0
    assert room["quantity"] == 3
    assert folio["metadata"]["migration_id"] == "backfill_booking_prices_v1"


async def test_backfill_folio_dry_run_does_not_write(db):
    """--dry-run reporta el folio pero no lo escribe."""
    db.rate_plans.insert_one({"prop_id": 9010, "rate_plan_id": "RP-9010-flex", "base_rate": 100.0})
    _seed(db, "BK-BF-0012", prop_id=9010)
    _seed_folio(db, "BK-BF-0012", prop_id=9010)

    result = backfill_booking_prices(db, dry_run=True)
    assert result["folios_recomputed"] == 1
    folio = db.guest_folios.find_one({"booking_id": "BK-BF-0012"})
    assert folio["total_room"] == 0.0  # intacto
    assert folio.get("folio_backfilled_at") is None


async def test_backfill_skips_folio_without_room_posting(db):
    """Folio sin posting de habitación (p. ej. penalización de no-show) no se toca."""
    db.rate_plans.insert_one({"prop_id": 9011, "rate_plan_id": "RP-9011-flex", "base_rate": 120.0})
    _seed(db, "BK-BF-0013", prop_id=9011)
    _seed_folio(
        db, "BK-BF-0013", prop_id=9011,
        postings=[
            {
                "posting_id": ObjectId(),
                "type": "charge",
                "category": "Penalización",
                "concept": "No-show — penalización",
                "amount": 47.94,
                "quantity": 1,
                "unit_price": 47.94,
                "reference_id": "BK-BF-0013",
                "reference_type": "no_show_penalty",
                "posted_at": datetime.now(timezone.utc),
            }
        ],
        posting_count=1, total_charges=47.94, total_due=47.94,
    )

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1
    assert result["folios_recomputed"] == 0
    folio = db.guest_folios.find_one({"booking_id": "BK-BF-0013"})
    assert folio["total_due"] == 47.94  # intacto
    assert folio.get("folio_backfilled_at") is None


async def test_backfill_keeps_folio_with_existing_room_charge(db):
    """Folio cuyo posting de habitación ya tiene cargo real no se toca."""
    db.rate_plans.insert_one({"prop_id": 9012, "rate_plan_id": "RP-9012-flex", "base_rate": 120.0})
    _seed(db, "BK-BF-0014", prop_id=9012)
    _seed_folio(
        db, "BK-BF-0014", prop_id=9012,
        total_room=188.0, total_due=188.0,
        postings=[
            {
                "posting_id": ObjectId(),
                "type": "room",
                "category": "Habitación",
                "concept": "Habitación — 2 noche(s)",
                "amount": 188.0,
                "quantity": 2,
                "unit_price": 94.0,
                "reference_id": "BK-BF-0014",
                "reference_type": "booking",
                "posted_at": datetime.now(timezone.utc),
            }
        ],
    )

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1
    assert result["folios_recomputed"] == 0
    folio = db.guest_folios.find_one({"booking_id": "BK-BF-0014"})
    assert folio["total_room"] == 188.0  # intacto
    assert folio.get("folio_backfilled_at") is None


async def test_backfill_recomputes_invoice_totals(db):
    """La factura en $0 de una reserva backfilleada se recalcula (mirror de
    ``generate_invoice_for_booking``: room_subtotal = total/1.16, taxes =
    total − room_subtotal, subtotal = room_subtotal + extras de line_items,
    total = subtotal + taxes). El desglose de line_items se preserva."""
    db.rate_plans.insert_one({"prop_id": 9020, "rate_plan_id": "RP-9020-flex", "base_rate": 120.0})
    _seed(db, "BK-BF-0020", prop_id=9020)
    _seed_invoice(
        db, "BK-BF-0020", prop_id=9020,
        line_items=[
            {
                "item_id": "it-extra-1", "type": "additional_charge",
                "concept": "Minibar", "amount": 15.0, "quantity": 1,
                "total": 15.0, "created_at": datetime.now(timezone.utc),
            }
        ],
    )

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1
    assert result["invoices_recomputed"] == 1

    inv = db.reservation_invoices.find_one({"booking_id": "BK-BF-0020"})
    # room_subtotal = 360/1.16 = 310.34; taxes = 360 − 310.34 = 49.66
    assert inv["room_subtotal"] == 310.34
    assert inv["taxes"] == 49.66
    # extras de line_items preservados: subtotal = 310.34 + 15 = 325.34
    assert inv["extras_total"] == 15.0
    assert inv["subtotal"] == 325.34
    assert inv["total"] == 375.0
    assert len(inv["line_items"]) == 1  # desglose intacto
    assert inv["metadata"]["migration_id"] == "backfill_booking_prices_v1"
    assert inv["invoice_backfilled_at"] is not None
    # Mirror fact_reservation_invoices se actualiza en paralelo.
    mirror = db.fact_reservation_invoices.find_one({"booking_id": "BK-BF-0020"})
    assert mirror is not None
    assert mirror["total"] == 375.0


async def test_backfill_invoice_dry_run_does_not_write(db):
    """--dry-run reporta la factura pero no la escribe."""
    db.rate_plans.insert_one({"prop_id": 9021, "rate_plan_id": "RP-9021-flex", "base_rate": 100.0})
    _seed(db, "BK-BF-0021", prop_id=9021)
    _seed_invoice(db, "BK-BF-0021", prop_id=9021)

    result = backfill_booking_prices(db, dry_run=True)
    assert result["invoices_recomputed"] == 1
    inv = db.reservation_invoices.find_one({"booking_id": "BK-BF-0021"})
    assert inv["total"] == 0.0  # intacto
    assert inv.get("invoice_backfilled_at") is None


async def test_backfill_keeps_invoice_with_existing_total(db):
    """Factura con total real (> 0) no se toca — no es el estado roto."""
    db.rate_plans.insert_one({"prop_id": 9022, "rate_plan_id": "RP-9022-flex", "base_rate": 120.0})
    _seed(db, "BK-BF-0022", prop_id=9022)
    _seed_invoice(
        db, "BK-BF-0022", prop_id=9022,
        room_subtotal=500.0, subtotal=500.0, taxes=0.0, total=500.0,
    )

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1
    assert result["invoices_recomputed"] == 0
    inv = db.reservation_invoices.find_one({"booking_id": "BK-BF-0022"})
    assert inv["total"] == 500.0  # intacto
    assert inv.get("invoice_backfilled_at") is None


async def test_backfill_recomputes_pending_invoice_of_priced_booking(db):
    """Factura en $0 de una reserva YA backfilleada (con precio) se corrige.

    El barrido principal solo procesa reservas sin precio; las facturas rotas
    de reservas con precio (que quedaron en $0 al crear la factura antes del
    backfill) se recalculan en un segundo barrido. Este es el caso de la
    demo: ``INV-202607-0005/0006`` quedaron en $0 tras backfillear sus
    reservas en una corrida anterior.

    El booking se siembra YA con ``total_price`` (ausente del primer barrido
    por diseño) — el test ejercita SOLO el segundo barrido, no un doble
    camino.
    """
    db.rate_plans.insert_one({"prop_id": 9023, "rate_plan_id": "RP-9023-flex", "base_rate": 120.0})
    _seed(db, "BK-BF-0023", prop_id=9023, total_price=360.0)  # ya con precio
    _seed_invoice(
        db, "BK-BF-0023", prop_id=9023,
        line_items=[
            {
                "item_id": "it-pend-1", "type": "additional_charge",
                "concept": "Parking", "amount": 20.0, "quantity": 1,
                "total": 20.0, "created_at": datetime.now(timezone.utc),
            }
        ],
    )

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 0  # nada que backfillear (ya tenía precio)
    assert result["invoices_recomputed"] == 1

    inv = db.reservation_invoices.find_one({"booking_id": "BK-BF-0023"})
    # room_subtotal = 360/1.16 = 310.34; taxes = 49.66; extras = 20
    assert inv["room_subtotal"] == 310.34
    assert inv["taxes"] == 49.66
    assert inv["extras_total"] == 20.0
    assert inv["subtotal"] == 330.34
    assert inv["total"] == 380.0
    assert inv["metadata"]["migration_id"] == "backfill_booking_prices_v1"
    mirror = db.fact_reservation_invoices.find_one({"booking_id": "BK-BF-0023"})
    assert mirror is not None and mirror["total"] == 380.0


async def test_backfill_pending_invoice_dry_run_does_not_write(db):
    """El barrido de facturas pendientes respeta --dry-run."""
    db.rate_plans.insert_one({"prop_id": 9024, "rate_plan_id": "RP-9024-flex", "base_rate": 100.0})
    _seed(db, "BK-BF-0024", prop_id=9024, total_price=300.0)
    _seed_invoice(db, "BK-BF-0024", prop_id=9024)

    result = backfill_booking_prices(db, dry_run=True)
    assert result["invoices_recomputed"] == 1
    inv = db.reservation_invoices.find_one({"booking_id": "BK-BF-0024"})
    assert inv["total"] == 0.0  # intacto
    assert inv.get("invoice_backfilled_at") is None


async def test_backfill_skips_pending_invoice_without_priced_booking(db):
    """Factura rota cuya reserva sigue sin precio → no se toca (nada que usar)."""
    db.rate_plans.insert_one({"prop_id": 9025, "rate_plan_id": "RP-9025-flex", "base_rate": 120.0})
    _seed(db, "BK-BF-0025", prop_id=9025)  # sin precio
    _seed_invoice(db, "BK-BF-0025", prop_id=9025)

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1  # el barrido principal sí la backfillea
    assert result["invoices_recomputed"] == 1  # y su factura se corrige ahí
    inv = db.reservation_invoices.find_one({"booking_id": "BK-BF-0025"})
    assert inv["total"] > 0


async def test_backfill_folio_total_due_floored_at_zero(db):
    """total_due nunca queda negativo (mirror del floor de post_to_folio)."""
    db.rate_plans.insert_one({"prop_id": 9013, "rate_plan_id": "RP-9013-flex", "base_rate": 120.0})
    _seed(db, "BK-BF-0015", prop_id=9013)
    _seed_folio(
        db, "BK-BF-0015", prop_id=9013,
        total_payments=400.0, total_due=-400.0,
    )

    result = backfill_booking_prices(db)
    assert result["backfilled"] == 1
    assert result["folios_recomputed"] == 1
    folio = db.guest_folios.find_one({"booking_id": "BK-BF-0015"})
    assert folio["total_room"] == 360.0
    assert folio["total_due"] == 0.0  # 360 − 400 < 0 → floor en 0
