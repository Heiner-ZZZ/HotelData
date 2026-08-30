"""Integración guest ↔ recepción: mensajería (chat) y solicitudes de servicio.

Ticket "Mensajería y solicitudes no funcionan correctamente" — verifica el
envío, recepción y seguimiento entre HUÉSPED y RECEPCIÓN (solo esos dos roles):

1. El huésped envía un mensaje (portal /api/stay/guest/chat).
2. La recepción ve la conversación y el mensaje (inbox /api/stay/conversations)
   y responde.
3. El huésped lee la respuesta.
4. El huésped crea una solicitud de servicio (/api/stay/guest/requests).
5. La recepción la ve, la pone in_progress y completed.
6. El huésped ve su solicitud completada.

Se invocan las funciones de ruta directamente (se salta el Depends de auth de
HTTP para aislar la lógica de negocio + Mongo).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture
def seeded_stay(db):
    """Hotel + reserva + sesión activa para un huésped en la habitación 101."""
    prop_id = 9010
    db.dim_hotels.insert_one({
        "prop_id": prop_id, "hotel_name": "Stay Hotel", "display_name": "Stay Hotel",
    })
    booking_id = "BK-STAY-9010-01"
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "user_id": None,
        "prop_id": prop_id,
        "status": "confirmed",
        "stay_status": "checked_in",
        "guest_name": "Huesped Stay",
        "check_in_date": "2026-09-01",
        "check_out_date": "2026-09-05",
    })
    db.hotel_rooms.insert_one({
        "prop_id": prop_id, "hotel_room_id": "HR-STAY-101",
        "room_label": "101", "room_type_id": "RT-STAY", "is_active": True,
    })
    token = "TOK-STAY-9010-ABC"
    db.stay_sessions.insert_one({
        "token": token,
        "booking_id": booking_id,
        "prop_id": prop_id,
        "hotel_id": None,
        "room_label": "101",
        "hotel_room_id": "HR-STAY-101",
        "guest_name": "Huesped Stay",
        "check_in": "2026-09-01",
        "check_out": "2026-09-05",
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "active": True,
    })
    return {"prop_id": prop_id, "booking_id": booking_id, "token": token, "room": "101"}


STAFF_USER = {"username": "recepcion", "display_name": "Ana Recepción"}


def test_guest_staff_messaging_flow(db, seeded_stay):
    from src.app.modules.instay.routes import (
        get_conversation_messages,
        guest_get_messages,
        guest_send_message,
        list_conversations,
        staff_reply,
    )

    prop_id = seeded_stay["prop_id"]
    token = seeded_stay["token"]
    room = seeded_stay["room"]

    # 1. El huésped envía un mensaje.
    r = guest_send_message({"token": token, "message": "Hola, necesito toallas"})
    assert r.ok is True

    # 2. La recepción ve la conversación y el mensaje.
    convs = list_conversations(prop_id=prop_id, current_user=STAFF_USER)
    assert any(c.room_label == room and "toallas" in c.last_message for c in convs.conversations)
    msgs = get_conversation_messages(room, prop_id=prop_id, current_user=STAFF_USER)
    assert any(m.sender == "guest" and m.message == "Hola, necesito toallas" for m in msgs.messages)

    # 3. La recepción responde.
    r = staff_reply(room, {"message": "En un momento llevamos toallas"}, query_prop_id=prop_id, current_user=STAFF_USER)
    assert r.ok is True

    # 4. El huésped lee la respuesta.
    msgs = guest_get_messages(token)
    assert any(m.sender == "staff" and m.message == "En un momento llevamos toallas" for m in msgs.messages)


def test_guest_staff_service_requests_flow(db, seeded_stay):
    from src.app.modules.instay.routes import (
        guest_create_request,
        guest_list_requests,
        list_service_requests,
        update_service_request,
    )

    prop_id = seeded_stay["prop_id"]
    token = seeded_stay["token"]

    # 4. El huésped crea una solicitud de servicio.
    r = guest_create_request({"token": token, "request_type": "towels", "description": "2 toallas"})
    assert r.ok is True
    request_id = r.request_id
    assert request_id

    # 5. La recepción la ve, la pone in_progress y luego completed.
    # (Se pasan los Query explícitos: al llamar la ruta directa sin FastAPI,
    #  los defaults `Query(...)` no se resuelven solos.)
    reqs = list_service_requests(
        prop_id=prop_id, status_filter=None, room_id=None, page=1, page_size=20,
        current_user=STAFF_USER,
    )
    assert any(i.request_type == "towels" and i.status == "pending" for i in reqs.items)

    upd = update_service_request(request_id, {"status": "in_progress"}, query_prop_id=prop_id, current_user=STAFF_USER)
    assert upd.ok is True
    upd = update_service_request(
        request_id,
        {"status": "completed", "staff_response": "Entregadas"},
        query_prop_id=prop_id,
        current_user=STAFF_USER,
    )
    assert upd.ok is True

    # 6. El huésped ve su solicitud completada con la respuesta del staff.
    g_reqs = guest_list_requests(token)
    towel = next((i for i in g_reqs.items if i.request_type == "towels"), None)
    assert towel is not None
    assert towel.status == "completed"
    assert towel.staff_response == "Entregadas"
