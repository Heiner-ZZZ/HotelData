"""Sprint llegada tardía/no-show — política configurable por hotel.

Contrato (política recomendada para HotelData, sprint actual):

- ``hotel_policies`` gana tres campos hotel-wide (como ``early_check_in_*``):
  ``guaranteed_reservation`` (bool), ``late_arrival_cutoff`` (HH:MM) y
  ``no_show_execution`` (``next_day`` | ``same_day_cutoff`` | ``manual``).
- El auto no-show NUNCA procesa: hoteles con ejecución ``manual``, reservas
  garantizadas, ni reservas con llegada tardía declarada (``late_checkin``,
  ``estimated_arrival_time`` o ``declared_late_arrival``).
- El check-in admite la llegada tardía post-medianoche: reserva cuyo
  check-in fue AYER sigue siendo checkeable como ``late_arrival`` mientras no
  sea no-show y el check-out no haya vencido; las fechas NO se mueven.
- Recepción puede declarar llegada tardía (protege del auto no-show).

Seam: funciones puras de ``src.app.modules.reservations.service.late_arrival``
que reciben ``db`` (mismo patrón que el resto del módulo reservations).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from src.app.core.timezone import local_today
from src.app.modules.reservations.service.late_arrival import (
    declare_late_arrival,
    get_late_arrival_context,
    resolve_late_arrival_policy,
)

NO_SHOW_EXECUTIONS = ("next_day", "same_day_cutoff", "manual")


def _days_from_today(n: int) -> str:
    return (date.fromisoformat(local_today()) + timedelta(days=n)).isoformat()


def _seed_policy(db, prop_id: int = 991, **fields) -> None:
    doc = {
        "prop_id": prop_id,
        "room_type_id": "",
        "rate_plan_id": "",
        "season_id": "",
        "check_in_time": "15:00",
        "check_out_time": "12:00",
        **fields,
    }
    db.hotel_policies.insert_one(doc)


def _seed_booking(
    db,
    booking_id: str,
    *,
    check_in_date: str | None = None,
    check_out_date: str | None = None,
    stay_status: str | None = None,
    prop_id: int = 991,
    **extra,
) -> dict:
    doc = {
        "booking_id": booking_id,
        "prop_id": prop_id,
        "guest_name": "Late Guest",
        "status": "confirmed",
        "check_in_date": check_in_date or _days_from_today(0),
        "check_out_date": check_out_date or _days_from_today(2),
        "total_nights": 2,
        "total_price": 300.0,
        "currency": "USD",
        "is_test": True,
        **extra,
    }
    if stay_status is not None:
        doc["stay_status"] = stay_status
    db.booking_orders.insert_one(doc)
    return doc


# ── 1. Resolución de política ──────────────────────────────────────────


def test_policy_defaults_when_no_row(db) -> None:
    policy = resolve_late_arrival_policy(db, 991)
    assert policy["guaranteed_reservation"] is False
    assert policy["late_arrival_cutoff"] == "23:59"
    assert policy["no_show_execution"] == "next_day"


def test_policy_reads_custom_values(db) -> None:
    _seed_policy(
        db,
        guaranteed_reservation=True,
        late_arrival_cutoff="02:00",
        no_show_execution="manual",
    )
    policy = resolve_late_arrival_policy(db, 991)
    assert policy["guaranteed_reservation"] is True
    assert policy["late_arrival_cutoff"] == "02:00"
    assert policy["no_show_execution"] == "manual"


def test_policy_ignores_per_room_type_rows(db) -> None:
    """Solo la fila hotel-wide (room_type/rate_plan/season vacíos) define la
    política de llegada tardía — mismo contrato que early_check_in_*."""
    db.hotel_policies.insert_one({
        "prop_id": 991,
        "room_type_id": "RT-1",
        "rate_plan_id": "",
        "season_id": "",
        "guaranteed_reservation": True,
        "no_show_execution": "manual",
    })
    policy = resolve_late_arrival_policy(db, 991)
    assert policy["guaranteed_reservation"] is False
    assert policy["no_show_execution"] == "next_day"


def test_policy_normalizes_invalid_cutoff(db) -> None:
    _seed_policy(db, late_arrival_cutoff="25:99")
    policy = resolve_late_arrival_policy(db, 991)
    assert policy["late_arrival_cutoff"] == "23:59"


def test_policy_normalizes_invalid_execution(db) -> None:
    _seed_policy(db, no_show_execution="banana")
    policy = resolve_late_arrival_policy(db, 991)
    assert policy["no_show_execution"] == "next_day"


# ── 2. Contexto de llegada tardía ──────────────────────────────────────


def test_context_not_protected_by_default(db) -> None:
    booking = _seed_booking(db, "BK-LA-1")
    ctx = get_late_arrival_context(db, booking)
    assert ctx["protected_from_auto_no_show"] is False


def test_context_protected_when_declared_late_arrival(db) -> None:
    booking = _seed_booking(db, "BK-LA-2", declared_late_arrival=True)
    ctx = get_late_arrival_context(db, booking)
    assert ctx["protected_from_auto_no_show"] is True
    assert ctx["declared_late_arrival"] is True


def test_context_protected_when_guaranteed_reservation(db) -> None:
    _seed_policy(db, guaranteed_reservation=True)
    booking = _seed_booking(db, "BK-LA-3")
    ctx = get_late_arrival_context(db, booking)
    assert ctx["protected_from_auto_no_show"] is True


def test_context_protected_when_late_markers_present(db) -> None:
    for extra in ({"late_checkin": True}, {"estimated_arrival_time": "01:30"}):
        booking = _seed_booking(db, f"BK-LA-{extra}", **extra)
        ctx = get_late_arrival_context(db, booking)
        assert ctx["protected_from_auto_no_show"] is True


def test_context_late_arrival_window_when_checkin_yesterday(db) -> None:
    """Reserva de ayer + no no-show + check-out futuro → ventana abierta."""
    booking = _seed_booking(
        db, "BK-LA-WIN",
        check_in_date=_days_from_today(-1),
        check_out_date=_days_from_today(2),
    )
    ctx = get_late_arrival_context(db, booking)
    assert ctx["is_late_arrival_window"] is True
    assert ctx["check_in_days_ago"] == 1


def test_context_window_closed_when_no_show(db) -> None:
    booking = _seed_booking(
        db, "BK-LA-NS",
        check_in_date=_days_from_today(-1),
        check_out_date=_days_from_today(2),
        stay_status="no_show",
    )
    ctx = get_late_arrival_context(db, booking)
    assert ctx["is_late_arrival_window"] is False
    assert ctx["blocked_reason"] == "no_show"


def test_context_window_closed_when_checkout_passed(db) -> None:
    booking = _seed_booking(
        db, "BK-LA-CO",
        check_in_date=_days_from_today(-3),
        check_out_date=_days_from_today(-1),
    )
    ctx = get_late_arrival_context(db, booking)
    assert ctx["is_late_arrival_window"] is False
    assert ctx["blocked_reason"] == "stay_ended"


def test_context_window_closed_for_today_or_future(db) -> None:
    booking = _seed_booking(db, "BK-LA-TODAY", check_in_date=_days_from_today(0))
    ctx = get_late_arrival_context(db, booking)
    assert ctx["is_late_arrival_window"] is False


def test_context_window_closed_when_two_or_more_days_late(db) -> None:
    booking = _seed_booking(
        db, "BK-LA-2D",
        check_in_date=_days_from_today(-2),
        check_out_date=_days_from_today(2),
    )
    ctx = get_late_arrival_context(db, booking)
    assert ctx["is_late_arrival_window"] is False
    assert ctx["blocked_reason"] == "too_late"


# ── 3. Declarar llegada tardía (servicio) ──────────────────────────────


def test_declare_late_arrival_sets_flag_and_eta(db) -> None:
    _seed_booking(db, "BK-DECLARE")
    result = declare_late_arrival(
        db, "BK-DECLARE",
        declared=True,
        estimated_arrival_time="01:15",
        changed_by="recep.prueba",
    )
    assert result["declared_late_arrival"] is True
    assert result["estimated_arrival_time"] == "01:15"
    doc = db.booking_orders.find_one({"booking_id": "BK-DECLARE"})
    assert doc["declared_late_arrival"] is True
    assert doc["estimated_arrival_time"] == "01:15"
    history = db.booking_status_history.find_one({"booking_id": "BK-DECLARE"})
    assert "llegada tardía" in history["reason"].lower()


def test_declare_late_arrival_can_clear_flag(db) -> None:
    _seed_booking(db, "BK-DECLARE-2", declared_late_arrival=True)
    result = declare_late_arrival(db, "BK-DECLARE-2", declared=False, changed_by="recep.prueba")
    assert result["declared_late_arrival"] is False
    doc = db.booking_orders.find_one({"booking_id": "BK-DECLARE-2"})
    assert doc["declared_late_arrival"] is False


def test_declare_late_arrival_rejects_bad_eta(db) -> None:
    _seed_booking(db, "BK-DECLARE-3")
    with pytest.raises(ValueError):
        declare_late_arrival(
            db, "BK-DECLARE-3",
            declared=True,
            estimated_arrival_time="25:99",
            changed_by="recep.prueba",
        )


def test_declare_late_arrival_rejects_no_show_booking(db) -> None:
    _seed_booking(
        db, "BK-DECLARE-4",
        check_in_date=_days_from_today(-1),
        check_out_date=_days_from_today(2),
        stay_status="no_show",
    )
    with pytest.raises(ValueError) as excinfo:
        declare_late_arrival(db, "BK-DECLARE-4", declared=True, changed_by="recep.prueba")
    assert "no-show" in str(excinfo.value).lower()


def test_declare_late_arrival_rejects_cancelled(db) -> None:
    _seed_booking(db, "BK-DECLARE-5", status="cancelled")
    with pytest.raises(ValueError):
        declare_late_arrival(db, "BK-DECLARE-5", declared=True, changed_by="recep.prueba")


def test_declare_late_arrival_unknown_booking(db) -> None:
    with pytest.raises(ValueError):
        declare_late_arrival(db, "BK-NOPE", declared=True, changed_by="recep.prueba")
