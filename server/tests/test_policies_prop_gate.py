"""Policies: PUT /policies con gate por-hotel (Migración E).

Antes: ``require_permission("properties.update")`` GLOBAL — un usuario con el
código en su rol global podía actualizar políticas de CUALQUIER hotel, y el
``prop_id`` viajaba solo en el body (hueco del middleware).

Ahora: ``require_prop_permission("properties.update")`` con ``prop_id`` por
QUERY + consistencia query↔body — 400 sin contexto, 403 deny-by-default sin
``role_assignments`` (el rol global no es fallback), 400 si el body no
coincide con el query.
"""
from __future__ import annotations

import pytest
from _prop_gate_helpers import login, seed_hotel, seed_hotel_role, seed_user
from bson import ObjectId


def _seed_global_user(db) -> dict[str, str]:
    """Rol GLOBAL con properties.update (el hueco pre-E) sin role_assignment."""
    return seed_user(
        db,
        username="gerente_pol_global",
        role="gerente_pol_global",
        permissions=["properties.update"],
        assigned_hotels=[1],
    )


def _assign(db, user_id: str, prop_id: int, role_id: ObjectId) -> None:
    db.role_assignments.insert_one(
        {"user_id": ObjectId(user_id), "prop_id": prop_id, "role_id": role_id}
    )


_PUT_POLICIES = "/api/management/policies"
_BODY = {"prop_id": 1, "room_type_id": "", "season_id": "", "rate_plan_id": ""}


class TestPoliciesPutPropGate:
    @pytest.mark.asyncio
    async def test_put_400_without_query_prop_id_even_with_body(self, client, db):
        """El body con prop_id NO basta: sin query → 400 (hueco del middleware)."""
        creds = _seed_global_user(db)
        await login(client, creds)
        resp = await client.put(_PUT_POLICIES, json=_BODY)
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_put_403_global_role_without_hotel_assignment(self, client, db):
        """El código GLOBAL properties.update ya no basta: sin assignment → 403."""
        creds = _seed_global_user(db)
        await login(client, creds)
        resp = await client.put(_PUT_POLICIES, params={"prop_id": 1}, json=_BODY)
        assert resp.status_code == 403, resp.text

    @pytest.mark.asyncio
    async def test_put_400_on_body_query_mismatch(self, client, db):
        """prop_id del query y del body no coinciden → 400."""
        creds = _seed_global_user(db)
        role_id = seed_hotel_role(db, prop_id=1, name="gerente_hotel_1", permissions=["properties.update"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        await login(client, creds)
        resp = await client.put(
            _PUT_POLICIES,
            params={"prop_id": 1},
            json={**_BODY, "prop_id": 2},
        )
        assert resp.status_code == 400, resp.text

    @pytest.mark.asyncio
    async def test_put_200_with_hotel_role(self, client, db):
        """Rol del hotel con properties.update + prop_id en query → 200."""
        creds = _seed_global_user(db)
        role_id = seed_hotel_role(db, prop_id=1, name="gerente_hotel_1", permissions=["properties.update"])
        _assign(db, creds["user_id"], 1, role_id)
        seed_hotel(db, 1)
        await login(client, creds)
        resp = await client.put(_PUT_POLICIES, params={"prop_id": 1}, json=_BODY)
        assert resp.status_code == 200, resp.text
