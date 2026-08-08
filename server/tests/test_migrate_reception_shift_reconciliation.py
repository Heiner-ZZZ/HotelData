"""Tests for the historical reception-shift reconciliation helpers."""
from __future__ import annotations

from datetime import datetime, timezone

from scripts.migrate_reception_shift_reconciliation import (
    BUCKETS,
    bucket_for_datetime,
    checkout_timestamp,
    is_cash_payment,
    is_checkout_evidence,
    probable_demo,
    is_approved_historical_payment,
    is_approved_historical_checkout,
    is_approved_historical_folio,
    HORUZ_SHIFT_ID,
    _action_events,
)


def test_bucket_for_datetime_maps_morning_afternoon_and_night() -> None:
    assert bucket_for_datetime(datetime(2026, 7, 9, 7, 59, tzinfo=timezone.utc)) == "evening"
    assert bucket_for_datetime(datetime(2026, 7, 9, 8, 0, tzinfo=timezone.utc)) == "morning"
    assert bucket_for_datetime(datetime(2026, 7, 9, 15, 59, tzinfo=timezone.utc)) == "morning"
    assert bucket_for_datetime(datetime(2026, 7, 9, 16, 0, tzinfo=timezone.utc)) == "afternoon"
    assert bucket_for_datetime(datetime(2026, 7, 9, 23, 59, tzinfo=timezone.utc)) == "afternoon"


def test_bucket_definitions_have_cash_windows() -> None:
    assert set(BUCKETS) == {"morning", "afternoon", "evening"}
    assert BUCKETS["morning"] == (8 * 60, 16 * 60)
    assert BUCKETS["afternoon"] == (16 * 60, 24 * 60)
    assert BUCKETS["evening"] == (0, 8 * 60)


def test_only_confirmed_cash_payments_are_cash_shift_evidence() -> None:
    assert is_cash_payment({"method": "cash", "status": "confirmed"}) is True
    assert is_cash_payment({"method": "efectivo", "status": "refunded"}) is True
    assert is_cash_payment({"method": "card", "status": "confirmed"}) is False
    assert is_cash_payment({"method": "cash", "status": "failed"}) is False


def test_checkout_actual_is_cash_shift_evidence_even_for_web_booking() -> None:
    assert is_checkout_evidence({"stay_status": "checked_out", "check_out_date_actual": "2026-07-09"}) is True
    assert is_checkout_evidence({"stay_status": "checked_in", "check_out_date_actual": None}) is False
    assert is_checkout_evidence({"stay_status": "checked_out"}) is False


def test_checkout_timestamp_uses_actual_date_and_time_not_updated_at() -> None:
    value = checkout_timestamp(
        {
            "check_out_date_actual": "2026-07-09",
            "check_out_time_actual": "13:21",
            "updated_at": "2026-08-07T19:31:45+00:00",
        }
    )
    assert value == datetime(2026, 7, 9, 13, 21, tzinfo=timezone.utc)


def test_real_employee_with_test_note_is_not_classified_as_demo() -> None:
    assert probable_demo(
        {
            "employee": "Carlos Mendoza",
            "closing_notes": "Prueba flujo real API",
        }
    ) is False


def test_explicit_demo_employee_labels_are_classified_as_demo() -> None:
    assert probable_demo({"employee": "Recepcionista Prueba"}) is True
    assert probable_demo({"employee": "Recepcionista UI Test"}) is True
    assert probable_demo({"employee": "Super Admin Demo"}) is True


def test_reconciliation_only_accepts_reviewed_historical_payment() -> None:
    assert is_approved_historical_payment(
        {
            "_id": "6a5be0362b365ae1d36f6f7a",
            "booking_id": "BK-20260709132144-89DA890A",
            "method": "cash",
            "status": "refunded",
            "amount": 1.00,
            "paid_at": "2026-07-18T20:21:00+00:00",
        }
    ) is True
    assert is_approved_historical_payment(
        {"_id": "other", "method": "cash", "status": "confirmed", "amount": 1.00}
    ) is False
    assert is_approved_historical_payment(
        {
            "_id": "6a5be0362b365ae1d36f6f7a",
            "booking_id": "BK-20260709132144-89DA890A",
            "method": "cash",
            "status": "refunded",
            "amount": 2.00,
            "paid_at": "2026-07-18T20:21:00+00:00",
        }
    ) is False


def test_reconciliation_only_accepts_the_five_reviewed_checkouts() -> None:
    assert is_approved_historical_checkout(
        {
            "booking_id": "BK-20260630012717-DC5DF649",
            "stay_status": "checked_out",
            "check_out_date_actual": "2026-07-01",
            "check_out_time_actual": "03:43",
        }
    ) is True
    assert is_approved_historical_checkout(
        {
            "booking_id": "BK-not-reviewed",
            "stay_status": "checked_out",
            "check_out_date_actual": "2026-07-01",
            "check_out_time_actual": "03:43",
        }
    ) is False
    assert is_approved_historical_checkout(
        {
            "booking_id": "BK-20260630012717-DC5DF649",
            "stay_status": "checked_out",
            "check_out_date_actual": "2026-07-01",
            "check_out_time_actual": "04:00",
        }
    ) is False


def test_only_horuz_folio_is_eligible_and_it_must_reuse_an_existing_shift() -> None:
    assert HORUZ_SHIFT_ID == "6a763298f1b31b5a7a98e00e"
    assert is_approved_historical_folio(
        {"_id": "6a4fa390582bc64092e388a3"}
    ) is True
    assert is_approved_historical_folio(
        {"_id": "6a431c58484c641cb4a3fdc2"}
    ) is False


class _FakeCollection:
    def __init__(self, documents: list[dict]) -> None:
        self.documents = documents

    def find(self, *_args, **_kwargs):
        return list(self.documents)

    def find_one(self, query, *_args, **_kwargs):
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                return document
        return None


class _FakeDb:
    def __init__(self) -> None:
        self.reservation_payments = _FakeCollection([])
        self.guest_folios = _FakeCollection([])
        self.booking_orders = _FakeCollection([])


def test_horuz_folio_requires_the_reviewed_checkout_facts() -> None:
    db = _FakeDb()
    db.guest_folios.documents = [{"_id": "6a4fa390582bc64092e388a3", "prop_id": 1}]
    db.booking_orders.documents = [
        {
            "_id": "oid-horuz",
            "booking_id": "BK-20260709132144-89DA890A",
            "prop_id": 1,
            "shift_id": HORUZ_SHIFT_ID,
            "stay_status": "checked_out",
            "check_out_date_actual": "2026-08-06",
            "check_out_time_actual": "19:31",
        }
    ]

    assert _action_events(db, 1) == []


def test_horuz_folio_accepts_the_reviewed_checkout_date_and_existing_shift() -> None:
    db = _FakeDb()
    db.guest_folios.documents = [{"_id": "6a4fa390582bc64092e388a3", "prop_id": 1}]
    db.booking_orders.documents = [
        {
            "_id": "oid-horuz",
            "booking_id": "BK-20260709132144-89DA890A",
            "prop_id": 1,
            "shift_id": HORUZ_SHIFT_ID,
            "stay_status": "checked_out",
            "check_out_date_actual": "2026-08-07",
            "check_out_time_actual": "19:31",
        }
    ]

    events = _action_events(db, 1)

    assert len(events) == 1
    assert events[0]["kind"] == "folio"
    assert events[0]["preferred_shift_id"] == HORUZ_SHIFT_ID


def test_reviewed_cash_payment_accepts_seconds_after_the_reviewed_minute() -> None:
    assert is_approved_historical_payment(
        {
            "_id": "6a5be0362b365ae1d36f6f7a",
            "booking_id": "BK-20260709132144-89DA890A",
            "method": "cash",
            "status": "refunded",
            "amount": 1.00,
            "paid_at": "2026-07-18T20:21:10.955000+00:00",
        }
    ) is True


def test_action_events_include_only_reviewed_payment_checkout_and_horuz_folio() -> None:
    db = _FakeDb()
    existing_shift_id = HORUZ_SHIFT_ID
    db.reservation_payments.documents = [
        {
            "_id": "6a5be0362b365ae1d36f6f7a",
            "prop_id": 1,
            "booking_id": "BK-20260709132144-89DA890A",
            "method": "cash",
            "status": "refunded",
            "amount": 1.00,
            "paid_at": "2026-07-18T20:21:00+00:00",
        },
        {
            "_id": "unreviewed-cash",
            "prop_id": 1,
            "method": "cash",
            "status": "confirmed",
            "paid_at": "2026-07-19T20:21:00+00:00",
        },
    ]
    db.guest_folios.documents = [
        {"_id": "6a4fa390582bc64092e388a3", "prop_id": 1},
        {"_id": "6a431c58484c641cb4a3fdc2", "prop_id": 1},
    ]
    reviewed_checkouts = [
        ("BK-20260630012717-DC5DF649", "2026-07-01", "03:43"),
        ("BK-20260630060318-C76A2F39", "2026-07-02", "03:21"),
        ("BK-20260701032655-8F726DCE", "2026-07-04", "20:18"),
        ("BK-20260701033656-FD7049F6", "2026-08-01", "03:09"),
        ("BK-20260704164045-6992E4A7", "2026-07-05", "15:14"),
    ]
    db.booking_orders.documents = [
        {
            "_id": f"oid-{booking_id}",
            "booking_id": booking_id,
            "prop_id": 1,
            "stay_status": "checked_out",
            "check_out_date_actual": date,
            "check_out_time_actual": time,
        }
        for booking_id, date, time in reviewed_checkouts
    ] + [
        {
            "_id": "oid-unreviewed",
            "booking_id": "BK-unreviewed",
            "prop_id": 1,
            "stay_status": "checked_out",
            "check_out_date_actual": "2026-07-06",
            "check_out_time_actual": "10:00",
        },
        {
            "_id": "oid-horuz",
            "booking_id": "BK-20260709132144-89DA890A",
            "prop_id": 1,
            "shift_id": existing_shift_id,
            "stay_status": "checked_out",
            "check_out_date_actual": "2026-08-07",
            "check_out_time_actual": "15:00",
        },
    ]

    events = _action_events(db, 1)

    assert [event["kind"] for event in events] == ["payment", "folio", "checkout", "checkout", "checkout", "checkout", "checkout"]
    assert events[1]["preferred_shift_id"] == HORUZ_SHIFT_ID
    assert [event["doc"]["booking_id"] for event in events if event["kind"] == "checkout"] == [
        booking_id for booking_id, _, _ in reviewed_checkouts
    ]
