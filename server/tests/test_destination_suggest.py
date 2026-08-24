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


def _seed_places(db) -> None:
    """Seed a hotel and a country so the suggest endpoint returns typed items."""
    _seed_destinations(db)
    db.dim_hotels.update_one(
        {"prop_id": 777001},
        {"$set": {
            "prop_id": 777001,
            "display_name": "Hotel Lima Centro",
            "hotel_name": "Hotel Lima Centro",
            "city": "Lima",
            "prop_country_id": 169,
        }},
        upsert=True,
    )
    db.dim_visitor_countries.update_one(
        {"visitor_location_country_id": 42},
        {"$set": {
            "visitor_location_country_id": 42,
            "country_name": "Testlandia",
            "country_display_name": "Testlandia",
        }},
        upsert=True,
    )
    db.geo_catalog.update_one(
        {"type": "country", "code": "TT"},
        {"$set": {"type": "country", "code": "TT", "name": "Terranova"}},
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


# ── País / hotel / ciudad (filtro ampliado del welcome) ──────────────────


async def test_suggest_returns_hotel_matches_typed(db, client):
    """A query matching a hotel name returns a suggestion with type 'hotel'."""
    _seed_places(db)
    response = await client.get(
        "/api/hotels/destinations/suggest", params={"q": "Hotel Lima"}
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(it["type"] == "hotel" and "Hotel Lima Centro" in it["name"] for it in items)


async def test_suggest_returns_country_matches_typed(db, client):
    """A query matching a country name returns a suggestion with type 'country'."""
    _seed_places(db)
    response = await client.get(
        "/api/hotels/destinations/suggest", params={"q": "Testlandia"}
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(it["type"] == "country" and it["name"] == "Testlandia" for it in items)


async def test_suggest_ignores_geo_catalog_countries(db, client):
    """Los países del catálogo curado (geo_catalog) YA NO se sugieren.

    Opción B: la tabla de países de los hoteles es ``dim_visitor_countries``;
    ``geo_catalog`` dejó de ser fuente de países para hoteles/sugerencias.
    """
    _seed_places(db)
    response = await client.get(
        "/api/hotels/destinations/suggest", params={"q": "Terranova"}
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(it["name"] != "Terranova" for it in items)


async def test_suggest_city_still_typed_city(db, client):
    """Destination-name matches keep type 'city' (backward compatible)."""
    _seed_places(db)
    response = await client.get(
        "/api/hotels/destinations/suggest", params={"q": "Madrid"}
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(it["type"] == "city" for it in items)
    assert any(it["name"] == "Madrid" for it in items)


def _seed_search_hotels(db) -> None:
    """Seed three hotels + facts: uno por país, uno por nombre, uno por ciudad."""
    _seed_places(db)
    db.dim_hotels.update_one(
        {"prop_id": 777002},
        {"$set": {
            "prop_id": 777002,
            "display_name": "Hotel Testlandia Plaza",
            "hotel_name": "Hotel Testlandia Plaza",
            "city": "Capital",
            "prop_country_id": 42,
        }},
        upsert=True,
    )
    db.dim_hotels.update_one(
        {"prop_id": 777003},
        {"$set": {
            "prop_id": 777003,
            "display_name": "Hotel Quito Real",
            "hotel_name": "Hotel Quito Real",
            "city": "Quito",
        }},
        upsert=True,
    )
    # Solo el hotel de CIUDAD (777003) queda ligado al destino Quito (id 3)
    # vía fact: la búsqueda por ciudad resuelve por srch_destination_id en
    # fact, mientras que por nombre de hotel y por país resuelve por prop_id
    # directo en dim_hotels (sin depender del fact).
    db.fact_hotel_reservations.insert_one({
        "prop_id": 777003,
        "srch_destination_id": 3,
        "price_usd": 70.0,
        "click_bool": 1,
        "reserva_bool": 1,
        "promotion_flag": 0,
    })


async def test_search_filters_by_country(db, client):
    """destination=<país> devuelve SOLO hoteles de ese país."""
    _seed_search_hotels(db)
    response = await client.get(
        "/api/hotels/availability", params={"destination": "Testlandia", "page_size": 10}
    )
    assert response.status_code == 200
    payload = response.json()
    ids = [item["prop_id"] for item in payload["items"]]
    assert 777002 in ids
    assert 777001 not in ids  # Perú (169), no Testlandia (42)
    assert 777003 not in ids  # sin país → no Testlandia


async def test_search_filters_by_hotel_name(db, client):
    """destination=<nombre de hotel> devuelve SOLO ese hotel."""
    _seed_search_hotels(db)
    response = await client.get(
        "/api/hotels/availability",
        params={"destination": "Hotel Lima Centro", "page_size": 10},
    )
    assert response.status_code == 200
    payload = response.json()
    ids = [item["prop_id"] for item in payload["items"]]
    assert 777001 in ids
    assert 777002 not in ids
    assert 777003 not in ids


async def test_search_still_filters_by_city(db, client):
    """City-name destination still filters (regression guard)."""
    _seed_search_hotels(db)
    response = await client.get(
        "/api/hotels/availability", params={"destination": "Quito", "page_size": 10}
    )
    assert response.status_code == 200
    payload = response.json()
    ids = [item["prop_id"] for item in payload["items"]]
    assert 777003 in ids
    assert 777002 not in ids  # Quito es ciudad; Testlandia Plaza no está en Quito


async def test_search_ignores_geo_country_code(db, client):
    """Un hotel con SOLO geo_country_code (sin prop_country_id y sin el nombre
    del país en su nombre) NO matchea al buscar ese país.

    Opción B: el país del hotel se resuelve por ``prop_country_id`` →
    ``dim_visitor_countries``; ``geo_country_code`` dejó de consultarse.
    """
    _seed_search_hotels(db)
    db.dim_hotels.update_one(
        {"prop_id": 777004},
        {"$set": {
            "prop_id": 777004,
            "display_name": "Hotel Nocturno Inn",
            "hotel_name": "Hotel Nocturno Inn",
            "geo_country_code": "TT",
        }},
        upsert=True,
    )
    db.fact_hotel_reservations.insert_one({
        "prop_id": 777004,
        "srch_destination_id": 3,
        "price_usd": 60.0,
        "click_bool": 1,
        "reserva_bool": 1,
        "promotion_flag": 0,
    })
    response = await client.get(
        "/api/hotels/availability", params={"destination": "Terranova", "page_size": 10}
    )
    assert response.status_code == 200
    ids = [item["prop_id"] for item in response.json()["items"]]
    assert 777004 not in ids, "geo_country_code ya no debe matchear por país"
    assert 777001 not in ids


async def test_suggest_country_comes_only_from_visitor_table(db, client):
    """El país se sugiere UNA vez y SOLO desde dim_visitor_countries.

    Aunque el mismo nombre exista en geo_catalog (duplicado real históricamente:
    Bolivia legacy + geo BO), el catálogo curado ya no participa.
    """
    _seed_places(db)
    # Testlandia ya está en dim_visitor_countries (id 42); también la agregamos
    # a geo_catalog para verificar que se IGNORA (antes era el caso de dedup).
    db.geo_catalog.update_one(
        {"type": "country", "code": "TL"},
        {"$set": {"type": "country", "code": "TL", "name": "Testlandia"}},
        upsert=True,
    )
    response = await client.get(
        "/api/hotels/destinations/suggest", params={"q": "Testlandia", "limit": 5}
    )
    assert response.status_code == 200
    countries = [it for it in response.json()["items"] if it["type"] == "country"]
    assert len(countries) == 1
    assert countries[0]["name"] == "Testlandia"


async def test_suggest_never_starves_hotels_and_countries(db, client):
    """Un prefijo con MUCHAS ciudades no oculta hoteles ni países (fair mix)."""
    _seed_places(db)
    # 12 ciudades que matchean "Ciud" (llenarían el limit de 8 solo de cities)
    for i in range(1, 13):
        db.dim_destinations.update_one(
            {"srch_destination_id": 1000 + i},
            {"$set": {"srch_destination_id": 1000 + i, "destination_name": f"Ciudad Delta {i}"}},
            upsert=True,
        )
    db.dim_hotels.update_one(
        {"prop_id": 777010},
        {"$set": {
            "prop_id": 777010,
            "display_name": "Hotel Ciudadela Real",
            "hotel_name": "Hotel Ciudadela Real",
            "city": "Ciudadela",
        }},
        upsert=True,
    )
    response = await client.get(
        "/api/hotels/destinations/suggest", params={"q": "Ciud", "limit": 8}
    )
    assert response.status_code == 200
    items = response.json()["items"]
    types = {it["type"] for it in items}
    assert "hotel" in types, "las ciudades no deben acaparar todas las sugerencias"


async def test_suggest_survives_regex_metacharacters(db, client):
    """Un query con metacaracteres regex no rompe el endpoint (sin 500)."""
    _seed_places(db)
    for bad in ["(", "[", "*", "a.", "\\"]:
        response = await client.get(
            "/api/hotels/destinations/suggest", params={"q": bad, "limit": 3}
        )
        assert response.status_code == 200, f"q={bad!r} devolvió {response.status_code}"
        assert isinstance(response.json()["items"], list)


async def test_search_unmatched_destination_returns_empty(db, client):
    """Un destino que no matchea nada NO devuelve todos los hoteles (vacío)."""
    _seed_search_hotels(db)
    response = await client.get(
        "/api/hotels/availability", params={"destination": "Zzznohaytalugar", "page_size": 10}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 0
    assert payload["items"] == []
