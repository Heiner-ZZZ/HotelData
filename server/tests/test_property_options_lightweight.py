"""Lightweight property options: the property-selector and rooms options only
need ``prop_id`` + ``display_name`` per hotel, but ``list_partner_hotels``
enriches EVERY row with ``performance_for_prop`` (3 aggregates over the
800K-doc fact collection) + ``_operational_flags`` (6 counts). With
``page_size=200`` (rooms/options) that is ~9.5s; with page_size=10 + query
(property-selector) ~1.5s. The lightweight path returns the same ids/labels
without the per-hotel heavy enrichment.

Regression (2026-08): rooms/options and properties/options blocked the rooms
page for seconds while the frontend only needed names.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.modules.partner.services.properties import list_partner_hotels
from src.app.modules.partner.services.properties.listing import list_property_options


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user(*, role: str, assigned_hotels: list[int] | None = "MISSING") -> dict:
    doc = {
        "username": f"{role}_user",
        "primary_role": role,
        "is_active": True,
        "created_at": _now(),
    }
    if assigned_hotels != "MISSING":
        doc["assigned_hotels"] = assigned_hotels
    return doc


def _seed_hotels(db) -> None:
    db.dim_hotels.insert_many(
        [
            {"prop_id": 1, "hotel_name": "Hotel Uno", "display_name": "Hotel Uno"},
            {"prop_id": 2, "hotel_name": "Hotel Dos", "display_name": "Hotel Dos"},
            {"prop_id": 3, "hotel_name": "Hotel Tres", "display_name": "Hotel Tres"},
        ]
    )


def _heavy_keys(row: dict) -> list[str]:
    """Keys that only the enriched (heavy) listing should carry."""
    return [k for k in ("performance", "operational", "yield_score", "sync_latency_ms") if k in row]


# ── list_property_options: function-level ──


def test_property_options_returns_same_ids_as_enriched_listing(db):
    """Both paths resolve the same prop_ids for the same scope."""
    _seed_hotels(db)
    admin = _user(role="super_admin")

    light = list_property_options("", page=1, page_size=50, user=admin)
    heavy = list_partner_hotels("", page=1, page_size=50, user=admin)

    assert [i["prop_id"] for i in light["items"]] == [i["prop_id"] for i in heavy["items"]]
    assert light["total"] == heavy["total"] == 3


def test_property_options_items_are_lightweight(db):
    """No per-hotel heavy enrichment keys leak into the options payload."""
    _seed_hotels(db)
    admin = _user(role="super_admin")

    result = list_property_options("", page=1, page_size=50, user=admin)

    assert len(result["items"]) == 3
    for item in result["items"]:
        assert set(item.keys()) == {"prop_id", "display_name"}, item.keys()
        assert _heavy_keys(item) == []


def test_property_options_respects_hotel_scope(db):
    """Restricted role only sees its assigned hotels (deny-by-default)."""
    _seed_hotels(db)
    gerente = _user(role="gerente_hotel", assigned_hotels=[2])

    result = list_property_options("", page=1, page_size=50, user=gerente)

    assert [i["prop_id"] for i in result["items"]] == [2]
    assert result["total"] == 1


def test_property_options_denies_empty_scope(db):
    """Restricted role with no hotels → zero items (never the full catalog)."""
    _seed_hotels(db)
    gerente = _user(role="gerente_hotel", assigned_hotels=[])

    result = list_property_options("", page=1, page_size=50, user=gerente)

    assert result["total"] == 0
    assert result["items"] == []


def test_property_options_query_filters_by_name(db):
    """Query filters on display_name/hotel_name like the enriched listing."""
    _seed_hotels(db)
    admin = _user(role="super_admin")

    result = list_property_options("dos", page=1, page_size=50, user=admin)

    assert [i["prop_id"] for i in result["items"]] == [2]


def test_property_options_pagination_shape(db):
    """The options payload keeps the same pagination envelope."""
    _seed_hotels(db)
    admin = _user(role="super_admin")

    result = list_property_options("", page=1, page_size=2, user=admin)

    assert result["total"] == 3
    assert len(result["items"]) == 2
    assert result["has_next"] is True


# ── API-level: properties/options + rooms/options use the lightweight path ──


async def _login(client, username: str, password: str) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": username, "password": password},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_properties_options_api_lightweight_shape(client, db, admin_user):
    """GET /api/management/properties/options returns only id+name rows."""
    _seed_hotels(db)
    await _login(client, admin_user["username"], admin_user["password"])

    resp = await client.get(
        "/api/management/properties/options",
        params={"q": "", "page": 1, "page_size": 10},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["total"] == 3
    for prop in payload["properties"]:
        assert set(prop.keys()) == {"prop_id", "display_name"}, prop.keys()


@pytest.mark.asyncio
async def test_rooms_options_api_lightweight_shape(client, db, admin_user):
    """GET /api/management/rooms/options returns only id+name rows."""
    _seed_hotels(db)
    await _login(client, admin_user["username"], admin_user["password"])

    resp = await client.get("/api/management/rooms/options")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert len(payload["properties"]) == 3
    for prop in payload["properties"]:
        assert set(prop.keys()) == {"prop_id", "display_name"}, prop.keys()
