"""Performance regressions for properties dashboard + amenities options.

Two sibling bugs of the rooms-options one:

1. ``management_property_options`` (used by ``/api/management/amenities/options``)
   ran the ENRICHED listing (100 rows × performance aggregates + operational
   counts ≈ 5s) while the frontend only needs ``prop_id`` + ``display_name``.

2. ``list_partner_hotels`` only cached when ``user is None`` — the dashboard
   always passes the current user, so EVERY page load re-ran the catalog scan
   (distinct over the fact collection + full dim_hotels read) plus per-hotel
   enrichment. Caching must be safe across hotel scopes (never leak hotels
   between restricted roles).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.modules.partner.services.dashboard.reports import management_property_options
from src.app.modules.partner.services.properties import list_partner_hotels


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
    return [k for k in ("performance", "operational", "yield_score", "sync_latency_ms") if k in row]


# ── management_property_options (amenities/options) ──


def test_management_property_options_skips_enriched_listing(db, monkeypatch):
    """amenities/options only needs id+name — must NOT run the per-hotel
    enriched listing (100 × aggregates ≈ 5s). Spy fails the test if the
    heavy path is still called."""
    _seed_hotels(db)
    admin = _user(role="super_admin")

    import src.app.modules.partner.services.dashboard.reports as reports_module

    def _boom(*args, **kwargs):
        raise AssertionError("management_property_options must not call list_partner_hotels")

    monkeypatch.setattr(reports_module, "list_partner_hotels", _boom)

    result = management_property_options(user=admin)

    assert len(result) == 3
    for item in result:
        assert set(item.keys()) == {"prop_id", "display_name"}, item.keys()
        assert _heavy_keys(item) == []


def test_management_property_options_respects_scope(db):
    """Restricted role only sees its assigned hotels (deny-by-default)."""
    _seed_hotels(db)
    gerente = _user(role="gerente_hotel", assigned_hotels=[2])

    result = management_property_options(user=gerente)

    assert [i["prop_id"] for i in result] == [2]


# ── list_partner_hotels cache scope isolation ──


def test_list_partner_hotels_cache_never_leaks_between_scopes(db):
    """A restricted role must never read the unfiltered (super_admin) cache.

    Regression guard: the enriched listing is cached per hotel-scope; a
    gerente with assigned_hotels=[2] calling after a super_admin call must
    still see ONLY its own hotel, not the shared 'all' cache.
    """
    _seed_hotels(db)
    admin = _user(role="super_admin")
    gerente = _user(role="gerente_hotel", assigned_hotels=[2])

    # Prime the unfiltered cache first (super_admin full catalog)
    first = list_partner_hotels("", page=1, page_size=10, user=admin)
    assert first["total"] == 3

    # Restricted user afterwards → must NOT see the cached full catalog
    scoped = list_partner_hotels("", page=1, page_size=10, user=gerente)
    assert scoped["total"] == 1
    assert [i["prop_id"] for i in scoped["items"]] == [2]


def test_list_partner_hotels_cache_isolates_empty_scope(db):
    """Empty-scope role must NOT read the unfiltered cache either."""
    _seed_hotels(db)
    admin = _user(role="super_admin")
    gerente = _user(role="gerente_hotel", assigned_hotels=[])

    first = list_partner_hotels("", page=1, page_size=10, user=admin)
    assert first["total"] == 3

    scoped = list_partner_hotels("", page=1, page_size=10, user=gerente)
    assert scoped["total"] == 0
    assert scoped["items"] == []


@pytest.mark.asyncio
async def test_amenities_options_api_lightweight(client, db, admin_user):
    """GET /api/management/amenities/options returns light properties."""
    _seed_hotels(db)
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": admin_user["username"], "password": admin_user["password"]},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/management/amenities/options")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert len(payload["properties"]) == 3
    for prop in payload["properties"]:
        assert set(prop.keys()) == {"prop_id", "display_name"}, prop.keys()
