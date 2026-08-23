"""Ruta de declaración de llegada tardía + contexto en el detalle de check-in.

La recepción declara (o retira) una llegada tardía desde la UI de check-in; el
flag protege la reserva del auto no-show. El detalle expone el contexto
``late_arrival`` (ventana, política, protección) para que la UI muestre la
explicación correcta sin duplicar lógica.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.app.core.timezone import local_today
from src.app.modules.reservations.service._checkin_detail import get_check_in_detail
from tests.conftest import login


def _days_from_today(n: int) -> str:
    return (date.fromisoformat(local_today()) + timedelta(days=n)).isoformat()


def _seed_booking(
    db,
    booking_id: str,
    *,
    check_in: int = 0,
    check_out: int = 2,
    stay_status: str | None = None,
    **extra,
) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": 991,
        "guest_name": "Late Arrival Guest",
        "guest_email": "late@test.com",
        "status": "confirmed",
        "check_in_date": _days_from_today(check_in),
        "check_out_date": _days_from_today(check_out),
        "total_nights": 2,
        "total_price": 250.0,
        "currency": "USD",
        "is_test": True,
        **extra,
    }
    if stay_status is not None:
        doc["stay_status"] = stay_status
    db.booking_orders.insert_one(doc)


@pytest.mark.asyncio
async def test_declare_late_arrival_route_sets_flag(client, admin_user, db) -> None:
    _seed_booking(db, "BK-DECL-ROUTE")
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.post(
        "/api/management/check-ins/BK-DECL-ROUTE/declare-late-arrival?prop_id=991",
        json={"declared_late_arrival": True, "estimated_arrival_time": "01:45"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["declared_late_arrival"] is True
    assert body["estimated_arrival_time"] == "01:45"
    doc = db.booking_orders.find_one({"booking_id": "BK-DECL-ROUTE"})
    assert doc["declared_late_arrival"] is True
    assert doc["estimated_arrival_time"] == "01:45"


@pytest.mark.asyncio
async def test_declare_late_arrival_route_can_clear(client, admin_user, db) -> None:
    _seed_booking(db, "BK-DECL-CLEAR", declared_late_arrival=True)
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.post(
        "/api/management/check-ins/BK-DECL-CLEAR/declare-late-arrival?prop_id=991",
        json={"declared_late_arrival": False},
    )

    assert response.status_code == 200
    assert response.json()["declared_late_arrival"] is False
    doc = db.booking_orders.find_one({"booking_id": "BK-DECL-CLEAR"})
    assert doc["declared_late_arrival"] is False


@pytest.mark.asyncio
async def test_declare_late_arrival_route_rejects_bad_eta(client, admin_user, db) -> None:
    _seed_booking(db, "BK-DECL-BAD")
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.post(
        "/api/management/check-ins/BK-DECL-BAD/declare-late-arrival?prop_id=991",
        json={"declared_late_arrival": True, "estimated_arrival_time": "99:99"},
    )

    assert response.status_code == 400
    doc = db.booking_orders.find_one({"booking_id": "BK-DECL-BAD"})
    assert doc.get("declared_late_arrival") in (None, False)


@pytest.mark.asyncio
async def test_declare_late_arrival_route_rejects_no_show(client, admin_user, db) -> None:
    _seed_booking(db, "BK-DECL-NS", stay_status="no_show")
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.post(
        "/api/management/check-ins/BK-DECL-NS/declare-late-arrival?prop_id=991",
        json={"declared_late_arrival": True},
    )

    assert response.status_code == 400
    assert "no-show" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_declare_late_arrival_route_requires_check_ins_manage(client, db) -> None:
    """Sin autenticación (y sin check-ins.manage) → rechazo antes de tocar datos."""
    _seed_booking(db, "BK-DECL-DENIED")

    response = await client.post(
        "/api/management/check-ins/BK-DECL-DENIED/declare-late-arrival?prop_id=991",
        json={"declared_late_arrival": True},
    )
    assert response.status_code in (303, 401, 403)
    doc = db.booking_orders.find_one({"booking_id": "BK-DECL-DENIED"})
    assert doc.get("declared_late_arrival") in (None, False)


def test_check_in_detail_exposes_late_arrival_window(db) -> None:
    _seed_booking(db, "BK-CTX-WIN", check_in=-1, check_out=2)

    detail = get_check_in_detail("BK-CTX-WIN")

    late = detail["late_arrival"]
    assert late["is_late_arrival_window"] is True
    assert late["check_in_days_ago"] == 1
    assert late["declared_late_arrival"] is False
    assert late["no_show_execution"] == "next_day"
    assert late["late_arrival_cutoff"] == "23:59"
    assert late["blocked_reason"] is None


def test_check_in_detail_exposes_declared_late_arrival(db) -> None:
    _seed_booking(db, "BK-CTX-DECL", check_in=-1, check_out=2, declared_late_arrival=True)

    detail = get_check_in_detail("BK-CTX-DECL")

    late = detail["late_arrival"]
    assert late["declared_late_arrival"] is True
    assert late["protected_from_auto_no_show"] is True


def test_check_in_detail_exposes_recorded_early_arrival_clock(db) -> None:
    """El detalle debe transportar el sello local ya persistido, no recalcularlo
    contra el reloj actual al abrir la página."""
    _seed_booking(
        db,
        "BK-CTX-EARLY-RECORDED",
        check_in=0,
        check_out=2,
        stay_status="checked_in",
        check_in_mode="early_approved",
        check_in_date_actual="2026-08-14",
        check_in_time_actual="13:00",
        early_check_in_minutes=120,
        early_check_in_fee=25.0,
        early_check_in_approved_by="gerente.prueba",
        early_check_in_reason="Habitación lista",
    )

    detail = get_check_in_detail("BK-CTX-EARLY-RECORDED")

    assert detail["check_in_date_actual"] == "2026-08-14"
    assert detail["check_in_time_actual"] == "13:00"
    assert detail["early_check_in"]["recorded_mode"] == "early_approved"
    assert detail["early_check_in"]["actual_date"] == "2026-08-14"
    assert detail["early_check_in"]["actual_time"] == "13:00"


def test_check_in_detail_exposes_blocked_reason_no_show(db) -> None:
    _seed_booking(db, "BK-CTX-NS", check_in=-1, check_out=2, stay_status="no_show")

    detail = get_check_in_detail("BK-CTX-NS")

    late = detail["late_arrival"]
    assert late["is_late_arrival_window"] is False
    assert late["blocked_reason"] == "no_show"
