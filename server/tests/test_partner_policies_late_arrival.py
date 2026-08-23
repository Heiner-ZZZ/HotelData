"""Persistencia de la política de llegada tardía / no-show en el save de políticas.

El sprint de llegada tardía define tres campos configurables por hotel en
``hotel_policies`` (scope hotel-wide, mismo contrato que ``early_check_in_*``):

- ``guaranteed_reservation``  bool   — reserva garantizada (protege del auto no-show)
- ``late_arrival_cutoff``     HH:MM  — hora límite de llegada el día del check-in
- ``no_show_execution``       enum   — next_day | same_day_cutoff | manual

Estos tests cubren que ``PUT /api/management/policies`` los persista (solo en
scope hotel-wide, nunca en filas por tipo de habitación / plan tarifario) y que
``GET /api/management/policies`` los devuelva con sus defaults.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import login

pytestmark = pytest.mark.asyncio


def _seed_hotel(db, prop_id: int = 801) -> None:
    db.dim_hotels.insert_one(
        {"prop_id": prop_id, "hotel_name": "Hotel Late Arrival", "display_name": "Hotel Late Arrival"}
    )


async def _login_admin(client: AsyncClient, admin_user) -> None:
    await login(client, admin_user["username"], admin_user["password"])


def _policies_payload(**overrides) -> dict:
    payload = {
        "prop_id": 801,
        "check_in_time": "15:00",
        "check_out_time": "12:00",
        "cancellation_policy": "",
        "pet_policy": "",
        "children_policy": "",
        "extra_bed_policy": "",
        "payment_policy": "",
        "house_rules": "",
        "cancellation_hours": 48,
        "cancellation_penalty_percent": 100,
        "pets_allowed": False,
        "pet_fee": 0,
        "children_allowed": True,
        "extra_bed_fee": 0,
        "min_stay": 1,
        "max_stay": 30,
        "deposit_percent": 0,
        "deposit_required": False,
        "early_check_in_enabled": True,
        "early_check_in_courtesy_minutes": 60,
        "early_check_in_default_fee": 0,
        "guaranteed_reservation": True,
        "late_arrival_cutoff": "02:30",
        "no_show_execution": "manual",
    }
    payload.update(overrides)
    return payload


async def test_put_policies_saves_late_arrival_fields(client, admin_user, db) -> None:
    _seed_hotel(db)
    await _login_admin(client, admin_user)

    response = await client.put("/api/management/policies", params={"prop_id": 801}, json=_policies_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["guaranteed_reservation"] is True
    assert body["late_arrival_cutoff"] == "02:30"
    assert body["no_show_execution"] == "manual"
    doc = db.hotel_policies.find_one({"prop_id": 801, "room_type_id": {"$in": ["", None]}})
    assert doc["guaranteed_reservation"] is True
    assert doc["late_arrival_cutoff"] == "02:30"
    assert doc["no_show_execution"] == "manual"


async def test_get_policies_returns_late_arrival_defaults(client, admin_user, db) -> None:
    _seed_hotel(db)
    await _login_admin(client, admin_user)

    response = await client.get("/api/management/policies?prop_id=801")

    assert response.status_code == 200
    policies = response.json()["policies"]
    assert policies["guaranteed_reservation"] is False
    assert policies["late_arrival_cutoff"] == "23:59"
    assert policies["no_show_execution"] == "next_day"


async def test_put_policies_room_type_scope_ignores_late_arrival_fields(client, admin_user, db) -> None:
    """Late-arrival es política hotel-wide: una fila por tipo de habitación no
    debe pisar los valores globales (mismo contrato que early_check_in_*)."""
    _seed_hotel(db)
    await _login_admin(client, admin_user)
    db.hotel_policies.insert_one(
        {
            "prop_id": 801,
            "room_type_id": "",
            "rate_plan_id": "",
            "season_id": "",
            "guaranteed_reservation": True,
            "late_arrival_cutoff": "02:00",
            "no_show_execution": "manual",
        }
    )

    response = await client.put(
        "/api/management/policies",
        params={"prop_id": 801},
        json=_policies_payload(room_type_id="RT-STD", late_arrival_cutoff="04:00", guaranteed_reservation=False),
    )

    assert response.status_code == 200
    room_row = db.hotel_policies.find_one({"prop_id": 801, "room_type_id": "RT-STD"})
    assert "guaranteed_reservation" not in room_row
    assert "late_arrival_cutoff" not in room_row
    assert "no_show_execution" not in room_row
    # La fila hotel-wide conserva sus valores globales intactos.
    hotel_row = db.hotel_policies.find_one(
        {"prop_id": 801, "room_type_id": {"$in": ["", None]}, "rate_plan_id": {"$in": ["", None]}}
    )
    assert hotel_row["guaranteed_reservation"] is True
    assert hotel_row["late_arrival_cutoff"] == "02:00"


async def test_put_policies_rejects_bad_late_arrival_cutoff(client, admin_user, db) -> None:
    _seed_hotel(db)
    await _login_admin(client, admin_user)

    response = await client.put(
        "/api/management/policies",
        params={"prop_id": 801},
        json=_policies_payload(late_arrival_cutoff="99:99"),
    )

    assert response.status_code == 400
    assert "HH:MM" in response.json()["detail"]


async def test_put_policies_rejects_bad_no_show_execution(client, admin_user, db) -> None:
    _seed_hotel(db)
    await _login_admin(client, admin_user)

    response = await client.put(
        "/api/management/policies",
        params={"prop_id": 801},
        json=_policies_payload(no_show_execution="whenever"),
    )

    assert response.status_code == 400
