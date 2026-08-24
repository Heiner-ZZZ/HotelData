"""Zona "Estadías pasadas" del huésped — ``GET /api/reservations/past-stays``.

El huésped (``cliente``) necesita un listado READ-ONLY de sus estadías ya
finalizadas: check-outs completados y reservas marcadas como no-show. Cada
item trae ``read_only_reason`` (server-authoritative) que explica por qué no
hay acciones disponibles:

- ``no_show``       → quedó marcada como No Show (no se presentó en el check-in).
- ``dates_passed``  → las fechas de la estadía ya pasaron.

Contrato de seguridad: el scope es SIEMPRE ownership (``user_id`` FK del
booking == usuario autenticado); nunca se filtra por email ni se permiten
reservas ajenas.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from tests.conftest import _seed_user

CLIENTE_ROLE_PERMISSIONS = ["account.read", "account.update", "reservations.read"]


def _seed_cliente_role(db) -> ObjectId:
    role = db.roles.find_one({"role_name": "cliente"})
    if role:
        return role["_id"]
    return db.roles.insert_one(
        {
            "role_name": "cliente",
            "display_name": "Cliente",
            "permissions": CLIENTE_ROLE_PERMISSIONS,
            "is_system": True,
        }
    ).inserted_id


def _seed_past_booking(
    db,
    *,
    user_id: ObjectId,
    booking_id: str,
    stay_status: str,
    status: str = "confirmed",
    check_out_offset_days: int = -5,
    prop_id: int = 999,
    penalty: float | None = None,
) -> None:
    db.dim_hotels.update_one(
        {"prop_id": prop_id},
        {"$set": {"hotel_name": "Hotel Test", "display_name": "Hotel Test"}},
        upsert=True,
    )
    doc = {
        "booking_id": booking_id,
        "user_id": user_id,
        "prop_id": prop_id,
        "guest_name": "Huésped Prueba",
        "guest_email": "owner@test.com",
        "status": status,
        "stay_status": stay_status,
        "total_price": 150.0,
        "currency": "USD",
        "total_nights": 2,
        "check_in_date": "2026-08-01",
        # Relativa a hoy: negativo = pasado, positivo = futuro.
        "check_out_date": (
            datetime.now(timezone.utc) + timedelta(days=check_out_offset_days)
        ).strftime("%Y-%m-%d"),
        "created_at": datetime.now(timezone.utc),
    }
    if penalty is not None:
        doc["no_show_penalty_amount"] = penalty
    db.booking_orders.insert_one(doc)


class TestPastStaysGuestZone:
    @pytest.mark.asyncio
    async def test_lista_sus_estadias_pasadas_con_razon(self, client, db, cliente_user):
        _seed_cliente_role(db)
        uid = ObjectId(cliente_user["user_id"])
        _seed_past_booking(db, user_id=uid, booking_id="BK-PAST-NS", stay_status="no_show",
                           check_out_offset_days=-3, penalty=75.0)
        _seed_past_booking(db, user_id=uid, booking_id="BK-PAST-OUT", stay_status="checked_out",
                           check_out_offset_days=-10)
        # Fechas pasadas pero stay_status sin cerrar → entra por dates_passed.
        _seed_past_booking(db, user_id=uid, booking_id="BK-PAST-DATES", stay_status="pending",
                           check_out_offset_days=-20)
        # NO deben aparecer:
        _seed_past_booking(db, user_id=uid, booking_id="BK-FUTURE", stay_status="pending",
                           check_out_offset_days=+30)
        other = ObjectId()
        _seed_past_booking(db, user_id=other, booking_id="BK-OTHER", stay_status="no_show",
                           check_out_offset_days=-1)
        _seed_past_booking(db, user_id=uid, booking_id="BK-CANCELLED", stay_status="checked_out",
                           status="cancelled", check_out_offset_days=-7)

        resp = await client.post(
            "/api/auth/login",
            json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
        )
        assert resp.status_code == 200

        res = await client.get("/api/reservations/past-stays")
        assert res.status_code == 200, res.text
        body = res.json()

        ids = {i["booking_id"]: i for i in body["items"]}
        assert set(ids.keys()) == {"BK-PAST-NS", "BK-PAST-OUT", "BK-PAST-DATES"}

        assert ids["BK-PAST-NS"]["read_only_reason"] == "no_show"
        assert ids["BK-PAST-NS"]["no_show_penalty_amount"] == 75.0
        assert ids["BK-PAST-OUT"]["read_only_reason"] == "dates_passed"
        assert ids["BK-PAST-DATES"]["read_only_reason"] == "dates_passed"

        # Orden: más reciente primero (check_out desc).
        ordered = [i["booking_id"] for i in body["items"]]
        assert ordered.index("BK-PAST-NS") < ordered.index("BK-PAST-OUT") < ordered.index("BK-PAST-DATES")

    @pytest.mark.asyncio
    async def test_cliente_ajeno_no_ve_reservas_de_otro(self, client, db, cliente_user):
        """Regression de ownership: sin user_id filter, B vería las de A."""
        _seed_cliente_role(db)
        other = ObjectId()
        _seed_past_booking(db, user_id=other, booking_id="BK-AJENO", stay_status="checked_out",
                           check_out_offset_days=-4)

        assert (
            await client.post(
                "/api/auth/login",
                json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
            )
        ).status_code == 200

        res = await client.get("/api/reservations/past-stays")
        assert res.status_code == 200
        assert all(i["booking_id"] != "BK-AJENO" for i in res.json()["items"])

    @pytest.mark.asyncio
    async def test_sin_estadias_pasadas_devuelve_lista_vacia(self, client, db, cliente_user):
        _seed_cliente_role(db)

        assert (
            await client.post(
                "/api/auth/login",
                json={"identifier": cliente_user["username"], "password": cliente_user["password"]},
            )
        ).status_code == 200

        res = await client.get("/api/reservations/past-stays")
        assert res.status_code == 200
        assert res.json()["items"] == []
