"""TDD: cada mensaje del chat debe llevar el nombre del huésped de su reserva.

La bandeja de staff agrupa por habitación; cuando la misma habitación hospedó
huéspedes distintos en ventanas de tiempo distintas (historial), el staff solo
ve "Hab. 103" y no puede saber QUIÉN escribió cada mensaje. Como un chat real,
cada burbuja debe mostrar el huésped que estaba hospedado en esa hora/fecha —
la fuente autoritativa es ``booking_orders.guest_name`` vía el ``booking_id``
propio de cada mensaje.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from src.app.core.timezone import local_now


async def _login(client, admin_user) -> int:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": admin_user["username"], "password": admin_user["password"]},
    )
    return resp.status_code


def _seed_room_with_two_guests(db) -> None:
    """Room 103 hosted María (June) and later Juan (now); both chatted."""
    db.booking_orders.insert_one(
        {
            "booking_id": "BK-GUEST-OLD",
            "prop_id": 1,
            "guest_name": "María López",
            "stay_status": "checked_out",
        }
    )
    db.booking_orders.insert_one(
        {
            "booking_id": "BK-GUEST-CURRENT",
            "prop_id": 1,
            "guest_name": "Juan Pérez",
            "stay_status": "checked_in",
        }
    )
    db.stay_messages.insert_one(
        {
            "booking_id": "BK-GUEST-OLD",
            "prop_id": 1,
            "room_label": "103",
            "sender": "guest",
            "staff_name": "",
            "message": "mensaje de junio",
            "created_at": local_now() - timedelta(days=60),
            "read": True,
        }
    )
    db.stay_messages.insert_one(
        {
            "booking_id": "BK-GUEST-CURRENT",
            "prop_id": 1,
            "room_label": "103",
            "sender": "guest",
            "staff_name": "",
            "message": "mensaje de hoy",
            "created_at": local_now(),
            "read": False,
        }
    )
    db.stay_messages.insert_one(
        {
            "booking_id": "BK-GUEST-CURRENT",
            "prop_id": 1,
            "room_label": "103",
            "sender": "staff",
            "staff_name": "Recepción",
            "message": "hola!",
            "created_at": local_now(),
            "read": True,
        }
    )


class TestConversationMessagesCarryGuestName:
    @pytest.mark.asyncio
    async def test_each_message_resolves_guest_from_its_own_booking(self, client, db, admin_user):
        _seed_room_with_two_guests(db)

        assert await _login(client, admin_user) == 200
        resp = await client.get("/api/stay/conversations/103", params={"prop_id": 1})

        assert resp.status_code == 200, resp.text
        messages = resp.json()["messages"]
        assert len(messages) == 3, messages
        by_text = {m["message"]: m for m in messages}
        # The June message belongs to the June guest even though the room's
        # current stay is Juan's — history stays attributable per message.
        assert by_text["mensaje de junio"]["guest_name"] == "María López"
        assert by_text["mensaje de hoy"]["guest_name"] == "Juan Pérez"
        # Staff messages keep their own author attribution.
        assert by_text["hola!"]["guest_name"] == ""

    @pytest.mark.asyncio
    async def test_message_without_booking_falls_back_to_empty(self, client, db, admin_user):
        db.stay_messages.insert_one(
            {
                "booking_id": "",
                "prop_id": 1,
                "room_label": "104",
                "sender": "system",
                "staff_name": "",
                "message": "sesión creada",
                "created_at": local_now(),
                "read": True,
            }
        )

        assert await _login(client, admin_user) == 200
        resp = await client.get("/api/stay/conversations/104", params={"prop_id": 1})

        assert resp.status_code == 200, resp.text
        messages = resp.json()["messages"]
        assert messages[0]["guest_name"] == ""
