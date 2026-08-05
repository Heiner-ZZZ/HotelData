"""Front-desk shift gate + ``shift_id`` FK stamping tests.

Covers the OPERA-style cash-shift model introduced for front-desk ops:

1. ``get_active_shift_id`` resolves the open shift for a property.
2. ``create_folio`` stamps ``shift_id`` (ObjectId) when provided.
3. ``create_payment`` stamps ``shift_id`` when provided.

The route-level 409 gates (check-in/check-out complete, cash payments,
walk-in creation) live at the HTTP layer; those are exercised by the
smoke checks in the ops docs. These tests pin the service-layer contract:
a front-desk operation passes the shift id, and the document must carry it.
"""

from __future__ import annotations

from bson import ObjectId

from src.app.modules.reception import get_active_shift_id
from src.app.modules.billing.service import create_folio, create_payment
from src.app.modules.billing.schemas import PaymentCreate
from src.app.modules.reservations.service._helpers import utc_now


def _open_shift(db, prop_id: int = 999) -> ObjectId:
    result = db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "start_time": utc_now(),
            "transactions": [],
        }
    )
    return result.inserted_id


def _seed_booking(db, booking_id: str, prop_id: int = 999) -> None:
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": prop_id,
            "guest_name": "Shift Test Guest",
            "guest_email": "shift@test.local",
            "check_in_date": "2026-08-10",
            "check_out_date": "2026-08-11",
            "check_in_time": "15:00",
            "check_out_time": "12:00",
            "assigned_rooms": [],
            "total_price": 150.0,
            "total_nights": 1,
            "room_type_id": "RT-shift-test",
            "room_type_name": "Shift Test",
            "is_test": True,
            "created_at": utc_now(),
        }
    )


# NOTE: ``reception_shifts`` is NOT in conftest's TEST_COLLECTIONS, so shift
# docs survive between tests in this module. Each test uses its own prop_id to
# stay hermetic.

def test_get_active_shift_id_resolves_open_shift(db):
    shift_id = _open_shift(db, prop_id=997)
    assert get_active_shift_id(997) == str(shift_id)


def test_get_active_shift_id_none_when_no_open_shift(db):
    _open_shift(db, prop_id=996)
    assert get_active_shift_id(12345) is None  # different property
    assert get_active_shift_id(996) == str(db.reception_shifts.find_one({"prop_id": 996})["_id"])


def test_get_active_shift_id_none_after_shift_closed(db):
    shift_id = _open_shift(db, prop_id=995)
    db.reception_shifts.update_one({"_id": shift_id}, {"$set": {"status": "closed"}})
    assert get_active_shift_id(995) is None


def test_create_folio_stamps_shift_id(db):
    booking_id = "BK-SHIFT-FOLIO-TEST"
    _seed_booking(db, booking_id)
    shift_id = _open_shift(db, prop_id=994)

    folio = create_folio(booking_id, shift_id=str(shift_id))

    assert folio is not None
    stored = db.guest_folios.find_one({"booking_id": booking_id})
    assert stored is not None
    assert stored.get("shift_id") == shift_id


def test_create_folio_keeps_shift_id_null_for_web_channel(db):
    booking_id = "BK-SHIFT-FOLIO-WEB"
    _seed_booking(db, booking_id)

    folio = create_folio(booking_id)  # no shift_id — web-channel stay

    assert folio is not None
    stored = db.guest_folios.find_one({"booking_id": booking_id})
    assert stored is not None
    assert stored.get("shift_id") is None


def test_create_payment_stamps_shift_id(db):
    booking_id = "BK-SHIFT-PAYMENT-TEST"
    _seed_booking(db, booking_id)
    shift_id = _open_shift(db, prop_id=993)

    result = create_payment(
        PaymentCreate(booking_id=booking_id, amount=50.0, method="cash"),
        shift_id=str(shift_id),
    )

    assert result is not None
    stored = db.reservation_payments.find_one({"booking_id": booking_id})
    assert stored is not None
    assert stored.get("shift_id") == shift_id
