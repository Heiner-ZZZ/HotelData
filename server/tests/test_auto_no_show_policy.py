"""Auto no-show respeta la política configurable por hotel.

Regla del sprint: el job nocturno NO marca no-show automáticamente solo porque
pasó la medianoche cuando existe una llegada tardía declarada o una reserva
garantizada — y un hotel puede optar por ejecución ``manual`` (decisión humana)
o ``same_day_cutoff`` (mismo día a partir de la hora límite de llegada).
"""

from __future__ import annotations

from datetime import date, timedelta

from src.app.core.timezone import local_today
from src.app.modules.reservations.service.no_show import auto_process_no_shows


def _days_from_today(n: int) -> str:
    return (date.fromisoformat(local_today()) + timedelta(days=n)).isoformat()


def _seed_policy(db, prop_id: int = 991, **fields) -> None:
    db.hotel_policies.insert_one({
        "prop_id": prop_id,
        "room_type_id": "",
        "rate_plan_id": "",
        "season_id": "",
        **fields,
    })


def _seed_booking(db, booking_id: str, *, check_in: int, prop_id: int = 991, **extra) -> None:
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": prop_id,
        "guest_name": "No Show Guest",
        "guest_email": "ns@test.com",
        "status": "confirmed",
        "check_in_date": _days_from_today(check_in),
        "check_out_date": _days_from_today(check_in + 2),
        "total_nights": 2,
        "total_price": 200.0,
        "currency": "USD",
        "is_test": True,
        **extra,
    })


def _assert_stay(db, booking_id: str, expected: str) -> None:
    doc = db.booking_orders.find_one({"booking_id": booking_id})
    assert doc.get("stay_status") == expected, (
        f"{booking_id}: stay_status={doc.get('stay_status')!r}, esperado {expected!r}"
    )


def test_auto_no_show_skips_guaranteed_reservation(db) -> None:
    _seed_policy(db, guaranteed_reservation=True)
    _seed_booking(db, "BK-GUARANTEED", check_in=-2)
    _seed_booking(db, "BK-PLAIN", check_in=-2, prop_id=992)

    summary = auto_process_no_shows()

    _assert_stay(db, "BK-GUARANTEED", None)
    _assert_stay(db, "BK-PLAIN", "no_show")
    assert summary["skipped"]["guaranteed"] >= 1


def test_auto_no_show_skips_declared_late_arrival(db) -> None:
    _seed_booking(db, "BK-DECLARED", check_in=-2, declared_late_arrival=True)
    _seed_booking(db, "BK-PLAIN2", check_in=-2)

    summary = auto_process_no_shows()

    _assert_stay(db, "BK-DECLARED", None)
    _assert_stay(db, "BK-PLAIN2", "no_show")
    assert summary["skipped"]["declared_late_arrival"] >= 1


def test_auto_no_show_skips_late_markers(db) -> None:
    _seed_booking(db, "BK-ETA", check_in=-2, estimated_arrival_time="01:30")
    _seed_booking(db, "BK-LATE", check_in=-2, late_checkin=True)

    auto_process_no_shows()

    _assert_stay(db, "BK-ETA", None)
    _assert_stay(db, "BK-LATE", None)


def test_auto_no_show_skips_manual_hotel(db) -> None:
    _seed_policy(db, no_show_execution="manual")
    _seed_booking(db, "BK-MANUAL", check_in=-2)

    summary = auto_process_no_shows()

    _assert_stay(db, "BK-MANUAL", None)
    assert summary["skipped"]["manual"] >= 1


def test_auto_no_show_processes_unprotected_by_default(db) -> None:
    """Regresión: sin política (o con política por defecto) el job sigue
    procesando reservas vencidas sin marcas de llegada tardía."""
    _seed_booking(db, "BK-DEFAULT", check_in=-2)

    summary = auto_process_no_shows()

    _assert_stay(db, "BK-DEFAULT", "no_show")
    assert summary["processed"] >= 1


def test_auto_no_show_same_day_cutoff_processes_after_cutoff(db) -> None:
    """Ejecución ``same_day_cutoff``: con la hora límite ya pasada (00:00),
    una reserva SIN llegar de HOY es candidata a no-show el mismo día."""
    _seed_policy(db, no_show_execution="same_day_cutoff", late_arrival_cutoff="00:00")
    _seed_booking(db, "BK-SAME-DAY", check_in=0)

    summary = auto_process_no_shows()

    _assert_stay(db, "BK-SAME-DAY", "no_show")
    assert summary["processed"] >= 1


def test_auto_no_show_next_day_skips_same_day(db) -> None:
    """Ejecución ``next_day`` (default): la reserva de HOY no es candidata
    todavía — el no-show del mismo día requiere ejecución ``same_day_cutoff``."""
    _seed_booking(db, "BK-TODAY", check_in=0)

    summary = auto_process_no_shows()

    _assert_stay(db, "BK-TODAY", None)
    assert summary["processed"] == 0


def test_auto_no_show_future_date_never_candidate(db) -> None:
    _seed_policy(db, no_show_execution="same_day_cutoff", late_arrival_cutoff="00:00")
    _seed_booking(db, "BK-FUTURE", check_in=1)

    auto_process_no_shows()

    _assert_stay(db, "BK-FUTURE", None)
