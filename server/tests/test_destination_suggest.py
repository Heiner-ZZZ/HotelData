"""Tests for the public destination-suggestion endpoint.

The welcome booking bar needs a dynamic destination autocomplete that
filters options as the user types. No public endpoint existed for that
(map/geo suggest endpoints require `settings.read` / `users.manage`), so
the hotels module now exposes `GET /api/hotels/destinations/suggest` with
case-insensitive regex matching over `dim_destinations`.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


def _seed_destinations(db) -> None:
    """Seed a handful of destinations used by the suggest endpoint."""
    seeds = [
        {"srch_destination_id": 1, "destination_name": "Madrid"},
        {"srch_destination_id": 2, "destination_name": "Madrid Barajas"},
        {"srch_destination_id": 3, "destination_name": "Quito"},
        {"srch_destination_id": 4, "destination_name": "Barcelona"},
    ]
    for s in seeds:
        db.dim_destinations.update_one(
            {"srch_destination_id": s["srch_destination_id"]},
            {"$set": s},
            upsert=True,
        )


async def test_suggest_returns_matching_destinations(db, client):
    """GET /api/hotels/destinations/suggest?q=Mad returns Madrid matches."""
    _seed_destinations(db)
    response = await client.get("/api/hotels/destinations/suggest", params={"q": "Mad"})
    assert response.status_code == 200
    payload = response.json()
    names = [item["name"] for item in payload["items"]]
    assert "Madrid" in names
    assert "Madrid Barajas" in names
    assert "Quito" not in names
    assert all("mad" in n.lower() for n in names)


async def test_suggest_is_case_insensitive(db, client):
    """Lowercase query matches uppercase destination names."""
    _seed_destinations(db)
    response = await client.get("/api/hotels/destinations/suggest", params={"q": "madrid"})
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert "Madrid" in names


async def test_suggest_limits_results(db, client):
    """The limit query param caps the result set."""
    _seed_destinations(db)
    response = await client.get(
        "/api/hotels/destinations/suggest", params={"q": "a", "limit": 2}
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) <= 2


async def test_suggest_empty_query_returns_empty(db, client):
    """An empty or whitespace query yields no suggestions."""
    _seed_destinations(db)
    response = await client.get("/api/hotels/destinations/suggest", params={"q": ""})
    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_suggest_returns_destination_ids(db, client):
    """Each suggestion carries its srch_destination_id for navigation."""
    _seed_destinations(db)
    response = await client.get("/api/hotels/destinations/suggest", params={"q": "Quito"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == 3
    assert items[0]["name"] == "Quito"


async def test_suggest_requires_no_auth(db, client):
    """The endpoint is public — unauthenticated requests succeed."""
    _seed_destinations(db)
    response = await client.get("/api/hotels/destinations/suggest", params={"q": "Mad"})
    assert response.status_code == 200
