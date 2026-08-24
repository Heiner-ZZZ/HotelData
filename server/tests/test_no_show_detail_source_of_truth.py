"""Fuente de verdad del importe a cobrar en no-show.

Cuando una reserva queda en no-show, lo que el huésped debe pagar es la
PENALIZACIÓN de la primera noche (folio de penalización + campos
``no_show_penalty_*`` del booking) — NO la factura de la estadía ($188,
generada al confirmar, cuando nunca hubo estancia). El detalle de la reserva
debe exponer el folio de penalización para que la UI muestre el importe
correcto en lugar de la factura como "pendiente de pago".
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.app.modules.reservations.service.queries import get_booking_detail


def _seed_booking(db, booking_id: str, **overrides) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "No Show Guest",
        "guest_email": "noshow@test.com",
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


def test_no_show_detail_exposes_penalty_folio(db):
    """El detalle de una reserva no-show expone el folio de penalización
    (la fuente de verdad del importe a cobrar)."""
    booking_id = "BK-NS-FOLIO"
    _seed_booking(
        db,
        booking_id,
        stay_status="no_show",
        no_show_penalty_amount=47.94,
        no_show_penalty_percent=51,
    )
    db.guest_folios.insert_one({
        "folio_number": "FL-NS-BK-NS-FOLIO",
        "booking_id": booking_id,
        "prop_id": 1,
        "status": "open",
        "total_due": 47.94,
        "postings": [{
            "type": "charge",
            "category": "Penalización",
            "reference_type": "no_show_penalty",
            "amount": 47.94,
        }],
        "created_at": datetime.now(timezone.utc),
    })

    detail = get_booking_detail(booking_id)

    assert detail is not None
    assert detail["booking"]["stay_status"] == "no_show"
    assert detail["booking"]["no_show_penalty_amount"] == 47.94
    assert detail["booking"]["no_show_penalty_percent"] == 51
    assert detail["no_show_folio_number"] == "FL-NS-BK-NS-FOLIO"


def test_non_no_show_has_no_penalty_folio(db):
    """Una reserva confirmada normal no expone folio de penalización."""
    booking_id = "BK-NORMAL-NO-FOLIO"
    _seed_booking(db, booking_id, stay_status="pending")

    detail = get_booking_detail(booking_id)

    assert detail is not None
    assert detail["no_show_folio_number"] is None
