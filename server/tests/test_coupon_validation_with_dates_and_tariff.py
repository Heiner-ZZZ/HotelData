"""TDD RED: validación de cupón debe verificar relación correcta tarifaria y ventana de fechas.

El huésped ve LUNA15 (-15% Tarifa Flexible) y VERANO20 (-20% 2026-08-01→2026-10-31 Tarifa Flexible)
solo vía Código Promocional en /account/bookings/new. Hoy la validación solo chequea
is_active/prop_id, no si la tarifa/habitación elegida está relacionada ni si las fechas
de la reserva caen dentro de la ventana de la promoción.
"""
from __future__ import annotations

import pytest
from datetime import date, timedelta

from src.app.core.timezone import local_today
from src.app.modules.reservations.service.lifecycle.create._validation import validate_coupon_code

pytestmark = pytest.mark.asyncio


def _seed_campaign(db, campaign_id: str, prop_id: int, start: str, end: str, rate_plans: list[str] | None, discount: int = 15):
    doc = {
        "campaign_id": campaign_id,
        "prop_id": prop_id,
        "name": f"Campaña {campaign_id}",
        "description": "Test",
        "discount_percent": discount,
        "start_date": start,
        "end_date": end,
        "is_active": True,
        "coupon_count": 1,
        "updated_at": "2026-08-23T00:00:00",
    }
    if rate_plans is not None:
        doc["applicable_rate_plan_ids"] = rate_plans
    db.promotion_campaigns.update_one({"campaign_id": campaign_id}, {"$set": doc}, upsert=True)
    return doc


def _seed_coupon(db, code: str, campaign_id: str, prop_id: int, discount: int = 15):
    db.coupon_codes.update_one(
        {"coupon_code": code},
        {"$set": {"coupon_code": code, "campaign_id": campaign_id, "prop_id": prop_id, "discount_percent": discount, "is_active": True, "is_deleted": {"$ne": True}, "used": False}},
        upsert=True,
    )
    # Ensure is_deleted field is correctly set for validation (the previous upsert used {"$ne": True} which is not a valid value, so we fix)
    db.coupon_codes.update_one({"coupon_code": code}, {"$unset": {"is_deleted": ""}})


def _seed_rate_plan(db, prop_id: int, rate_plan_id: str, room_types: list[str]):
    db.rate_plans.update_one(
        {"rate_plan_id": rate_plan_id},
        {"$set": {"rate_plan_id": rate_plan_id, "prop_id": prop_id, "name": f"Plan {rate_plan_id}", "base_rate": 100.0, "is_active": True, "applicable_room_types": room_types}},
        upsert=True,
    )


async def test_coupon_fails_when_dates_outside_window(db):
    """VERANO20 2026-08-01→2026-10-31 debe fallar si la reserva es fuera de ventana."""
    prop_id = 92001
    campaign_id = "PC-92001-verano"
    # Campaign válida solo en agosto-octubre, solo para Tarifa Flexible
    _seed_campaign(db, campaign_id, prop_id, "2026-08-01", "2026-10-31", ["RP-92001-flex"], discount=20)
    _seed_coupon(db, "VERANO20-TDD", campaign_id, prop_id, discount=20)
    _seed_rate_plan(db, prop_id, "RP-92001-flex", ["RT-A"])
    _seed_rate_plan(db, prop_id, "RP-92001-other", ["RT-A"])

    # Dentro de ventana y con tarifa correcta -> válido
    err, disc, _ = validate_coupon_code("VERANO20-TDD", prop_id, check_in="2026-08-15", check_out="2026-08-16", rate_plan_id="RP-92001-flex")
    assert err is None, f"debería ser válido dentro de ventana con tarifa correcta: {err}"
    assert disc == 20

    # Fuera de ventana (noviembre) -> inválido aunque tarifa correcta
    err, disc, _ = validate_coupon_code("VERANO20-TDD", prop_id, check_in="2026-11-01", check_out="2026-11-02", rate_plan_id="RP-92001-flex")
    assert err is not None
    assert "fuera de la ventana" in err.lower() or "vigencia" in err.lower() or "fecha" in err.lower()

    # Dentro de ventana pero tarifa incorrecta -> inválido
    err, disc, _ = validate_coupon_code("VERANO20-TDD", prop_id, check_in="2026-08-15", check_out="2026-08-16", rate_plan_id="RP-92001-other")
    assert err is not None
    assert "tarifa" in err.lower() or "no aplica" in err.lower()


async def test_coupon_fails_when_tariff_not_related_to_room(db):
    """LUNA15 -15% Tarifa Flexible debe fallar si la reserva usa Tarifa Desayuno o habitación no cubierta."""
    prop_id = 92002
    campaign_id = "PC-92002-luna"
    # LUNA15 sin ventana (siempre vigente) pero solo para Flexible
    _seed_campaign(db, campaign_id, prop_id, "", "", ["RP-92002-flex"], discount=15)
    _seed_coupon(db, "LUNA15-TDD", campaign_id, prop_id, discount=15)
    _seed_rate_plan(db, prop_id, "RP-92002-flex", ["RT-STD"])
    _seed_rate_plan(db, prop_id, "RP-92002-desayuno", ["RT-VIP"])

    # Con tarifa correcta -> válido
    err, disc, _ = validate_coupon_code("LUNA15-TDD", prop_id, check_in="2026-08-24", check_out="2026-08-26", rate_plan_id="RP-92002-flex", room_type_id="RT-STD")
    assert err is None

    # Con tarifa incorrecta (desayuno) -> inválido aunque habitación exista
    err, disc, _ = validate_coupon_code("LUNA15-TDD", prop_id, check_in="2026-08-24", check_out="2026-08-26", rate_plan_id="RP-92002-desayuno", room_type_id="RT-VIP")
    assert err is not None
    assert "tarifa" in err.lower()

    # Con tarifa correcta pero habitación no cubierta por esa tarifa (ej. RT-VIP no está en flex) -> inválido
    err, disc, _ = validate_coupon_code("LUNA15-TDD", prop_id, check_in="2026-08-24", check_out="2026-08-26", rate_plan_id="RP-92002-flex", room_type_id="RT-VIP")
    assert err is not None
    # Debe mencionar habitación o tarifa
    assert "habitaci" in err.lower() or "tarifa" in err.lower()


async def test_coupon_valid_when_no_specific_tariff_and_no_dates(db):
    """Si la campaña no tiene applicable_rate_plan_ids ni ventana, aplica a todo el hotel."""
    prop_id = 92003
    campaign_id = "PC-92003-generica"
    _seed_campaign(db, campaign_id, prop_id, "", "", None, discount=10)  # None = aplica a todo
    _seed_coupon(db, "GEN10-TDD", campaign_id, prop_id, discount=10)
    _seed_rate_plan(db, prop_id, "RP-ANY", ["RT-ANY"])

    err, disc, _ = validate_coupon_code("GEN10-TDD", prop_id, check_in="2026-09-01", check_out="2026-09-02", rate_plan_id="RP-ANY", room_type_id="RT-ANY")
    assert err is None
    assert disc == 10

    # También válido sin pasar rate_plan/room (reserva sin tarifa elegida aún)
    err, disc, _ = validate_coupon_code("GEN10-TDD", prop_id)
    assert err is None
