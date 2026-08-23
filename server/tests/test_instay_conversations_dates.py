"""TDD: ``GET /api/stay/conversations`` debe exponer las fechas de la reserva.

La clasificación activo vs historial del inbox de mensajería no puede depender
solo de ``stay_status`` (un ``pending`` puede quedar atascado cuando la reserva
ya terminó) ni del timestamp del último mensaje. Las fechas autoritativas viven
en ``booking_orders.check_in_date``/``check_out_date``.

El endpoint enriquecía ``check_in``/``check_out`` únicamente desde la sesión
ACTIVA del huésped (``stay_sessions``). Cuando el huésped ya hizo check-out la
sesión se desactiva, y esos campos llegaban vacíos — así que un chat de una
estadía terminada quedaba huérfano de fecha y no se podía mandar a "historial".

Estos tests fijan que las fechas vengan de la reserva aunque la sesión esté
inactiva.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from src.app.core.timezone import local_now


def _days_from_today(offset: int) -> str:
    return (local_now() + timedelta(days=offset)).strftime("%Y-%m-%d")


async def _login(client, identifier: str, password: str) -> int:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": identifier, "password": password},
    )
    return resp.status_code


def _seed_ended_conversation(db, *, booking_id: str, room_label: str) -> None:
    """A chat whose stay already ended: booking exists, but no active session."""
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 1,
            "guest_name": "Huésped Histórico",
            "check_in_date": _days_from_today(-3),
            "check_out_date": _days_from_today(-1),
            # Stale: the reservation ended but the status never got flipped.
            "stay_status": "pending",
        }
    )
    db.stay_messages.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 1,
            "room_label": room_label,
            "sender": "guest",
            "staff_name": "",
            "message": "gracias",
            "created_at": local_now() - timedelta(days=2),
            "read": True,
        }
    )


class TestConversationsExposeBookingDates:
    @pytest.mark.asyncio
    async def test_ended_stay_returns_reservation_dates(self, client, db, admin_user):
        """Sin sesión activa, check_in/check_out deben venir de booking_orders."""
        _seed_ended_conversation(db, booking_id="BK-CONV-ENDED", room_label="101")

        assert await _login(client, admin_user["username"], admin_user["password"]) == 200
        resp = await client.get("/api/stay/conversations", params={"prop_id": 1})

        assert resp.status_code == 200, resp.text
        convs = resp.json()["conversations"]
        assert len(convs) == 1, convs

        conv = convs[0]
        # Date-based fields survive the inactive session — the frontend can
        # classify this as "historial" (check_out < today) instead of "activa".
        assert conv["check_in"] == _days_from_today(-3)
        assert conv["check_out"] == _days_from_today(-1)
        assert conv["stay_status"] == "pending"
        assert conv["guest_name"] == "Huésped Histórico"

    @pytest.mark.asyncio
    async def test_active_session_dates_take_precedence(self, client, db, admin_user):
        """La sesión activa sigue mandando cuando existe (no regresión)."""
        _seed_ended_conversation(db, booking_id="BK-CONV-ACTIVE", room_label="102")
        db.stay_sessions.insert_one(
            {
                "booking_id": "BK-CONV-ACTIVE",
                "prop_id": 1,
                "room_label": "102",
                "guest_name": "Huésped Activo",
                "check_in": _days_from_today(-1),
                "check_out": _days_from_today(2),
                "active": True,
            }
        )

        assert await _login(client, admin_user["username"], admin_user["password"]) == 200
        resp = await client.get("/api/stay/conversations", params={"prop_id": 1})

        assert resp.status_code == 200, resp.text
        conv = resp.json()["conversations"][0]
        assert conv["check_in"] == _days_from_today(-1)
        assert conv["check_out"] == _days_from_today(2)
        assert conv["guest_name"] == "Huésped Activo"
