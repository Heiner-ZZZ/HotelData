"""GET /api/auth/registration-status — plan sugerido + bloque de pago (Fase 3 UI).

La pantalla ``/alojamiento-en-revision`` necesita, además del plan sugerido,
el vencimiento informativo (gracia inicial) y los métodos de pago manuales del
catálogo (sin pasarela bancaria).
"""

from __future__ import annotations

import pytest
from passlib.context import CryptContext

pytestmark = pytest.mark.asyncio

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _seed_owner(db) -> None:
    owner_id = db.users.insert_one(
        {
            "username": "owner_reg",
            "email": "owner_reg@hotel.local",
            "password_hash": _pwd.hash("OwnerPass123!"),
            "primary_role": "hotel_partner",
            "assigned_hotels": [42],
            "approval_status": "approved",
            "is_active": True,
            "created_at": None,
        }
    ).inserted_id
    db.dim_hotels.insert_one(
        {
            "prop_id": 42,
            "hotel_name": "Hotel Registro",
            "approval_status": "approved",
            "owner_user_id": owner_id,
            "total_rooms_declared": 20,
            "created_at": None,
        }
    )


async def test_registration_status_exposes_payment_block(client, db):
    _seed_owner(db)
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "owner_reg", "password": "OwnerPass123!"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/auth/registration-status")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Plan sugerido (ya existía).
    assert body["suggested_band"]["label"] == "Pequeño"
    assert body["suggested_band"]["monthly_usd"] == 89

    # Bloque de pago (nuevo).
    assert body["initial_grace_days"] == 7
    methods = body["payment_methods"]
    assert len(methods) == 3
    assert {m["code"] for m in methods} == {"bank_transfer", "cash_deposit", "manual_online"}
    for method in methods:
        assert method["label"]
        assert "details" in method
