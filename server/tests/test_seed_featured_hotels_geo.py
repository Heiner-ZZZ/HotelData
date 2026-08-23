"""TDD: contrato del seed que completa/corrige los hoteles destacados 1–5.

Los props 1–5 (Hotel Lima Centro, Resort Cancún Playa, Hotel Quito Histórico,
Hotel Buenos Aires Elegance, Hotel Santiago Business) estaban incompletos y con
relaciones de país erróneas (heredadas de ``seed_featured_hotels.py``: ids
legacy incorrectos que apuntaban a placeholders XX-N). Este seed:

- Les agrega latitud/longitud, descripción (espejada a hotel_content_pages),
  dirección, moneda local y rating.
- Corrige la relación de PAÍS contra ``dim_visitor_countries`` (la FK real de
  ``prop_country_id``): Perú=219, México=148, Ecuador=60, Argentina=13, Chile=44.
  NO escribe campos del catálogo curado (geo_country_code/geo_catalog_id).
- Vincula la CIUDAD contra ``dim_destinations`` vía ``srch_destination_id``
  (Lima=89, Cancún=311, Buenos Aires=7, Santiago=168). Quito no está en
  dim_destinations → sin srch_destination_id (city queda como texto).
- Idempotente y nunca crea relaciones huérfanas: aborta si el país del dataset
  no existe en ``dim_visitor_countries``.
"""

from __future__ import annotations

import pytest

from scripts.seed_featured_hotels_geo import FEATURED_GEO, seed

# dim_visitor_countries: los 5 países del dataset (FK legacy de prop_country_id).
VISITOR_COUNTRIES = [
    {"visitor_location_country_id": 219, "country_name": "Perú", "country_display_name": "Perú"},
    {"visitor_location_country_id": 148, "country_name": "México", "country_display_name": "México"},
    {"visitor_location_country_id": 60, "country_name": "Ecuador", "country_display_name": "Ecuador"},
    {"visitor_location_country_id": 13, "country_name": "Argentina", "country_display_name": "Argentina"},
    {"visitor_location_country_id": 44, "country_name": "Chile", "country_display_name": "Chile"},
]

# dim_destinations: destinos canónicos de las ciudades de los props 1-5 (Quito no existe).
DESTINATIONS = [
    {"srch_destination_id": 89, "destination_name": "Lima"},
    {"srch_destination_id": 311, "destination_name": "Cancún"},
    {"srch_destination_id": 7, "destination_name": "Buenos Aires"},
    {"srch_destination_id": 168, "destination_name": "Santiago"},
]

# prop_id → (country id, geo code, destino esperado o None)
EXPECTED = {
    1: (219, "PE", 89),
    2: (148, "MX", 311),
    3: (60, "EC", None),
    4: (13, "AR", 7),
    5: (44, "CL", 168),
}


@pytest.fixture(autouse=True)
def _geo_fixtures(db):
    # Opción B: el seed ya NO consulta geo_catalog para los hoteles — la
    # dejamos vacía para que nada dependa de ella en estos tests.
    db.geo_catalog.delete_many({})
    db.dim_visitor_countries.delete_many({})
    db.dim_visitor_countries.insert_many(VISITOR_COUNTRIES)
    db.dim_destinations.delete_many({})
    db.dim_destinations.insert_many(DESTINATIONS)
    return db


def test_seed_creates_5_hotels_with_full_profile(db, _geo_fixtures):
    stats = seed(db)
    assert stats["created"] == 5

    for entry in FEATURED_GEO:
        hotel = db.dim_hotels.find_one({"prop_id": entry["prop_id"]})
        assert hotel is not None, f"prop {entry['prop_id']} no creado"
        assert hotel["display_name"] == entry["display_name"]
        assert hotel["description"]
        assert hotel["address"]
        assert hotel["latitude"] is not None and hotel["longitude"] is not None
        assert -90 <= hotel["latitude"] <= 90 and -180 <= hotel["longitude"] <= 180
        assert hotel["currency"] == entry["currency"]
        assert hotel["currency"] in hotel["accepted_currencies"]
        assert hotel["active"] is True


def test_hotels_relate_to_correct_visitor_country(db, _geo_fixtures):
    seed(db)
    for prop_id, (country_id, _geo_code, _dest) in EXPECTED.items():
        visitor = db.dim_visitor_countries.find_one({"visitor_location_country_id": country_id})
        hotel = db.dim_hotels.find_one({"prop_id": prop_id})
        assert hotel["prop_country_id"] == country_id
        assert hotel["display_country_label"] == visitor["country_name"]


def test_hotels_have_no_geo_catalog_relation(db, _geo_fixtures):
    """Opción B: los hoteles NO llevan geo_country_code/geo_catalog_id/geo_city_*."""
    seed(db)
    for prop_id, (_country_id, _geo_code, _dest) in EXPECTED.items():
        hotel = db.dim_hotels.find_one({"prop_id": prop_id})
        for field in ("geo_country_code", "geo_catalog_id", "geo_city_code", "geo_city_id"):
            assert field not in hotel, f"prop {prop_id} aún tiene {field}"
        assert hotel["prop_country_id"] == _country_id
        assert db.dim_visitor_countries.count_documents({"visitor_location_country_id": _country_id}) == 1


def test_seed_does_not_create_geo_catalog_countries(db, _geo_fixtures):
    """Opción B: el seed NO agrega países al catálogo curado (geo_catalog)."""
    seed(db)
    assert db.geo_catalog.count_documents({"type": "country", "code": "EC"}) == 0
    assert db.geo_catalog.count_documents({"type": "country"}) == 0


def test_hotels_relate_to_dim_destinations(db, _geo_fixtures):
    seed(db)
    for prop_id, (_country_id, _geo_code, dest_id) in EXPECTED.items():
        hotel = db.dim_hotels.find_one({"prop_id": prop_id})
        if dest_id is not None:
            dest = db.dim_destinations.find_one({"srch_destination_id": dest_id})
            assert dest is not None
            assert hotel["srch_destination_id"] == dest_id
            assert hotel["city"] == dest["destination_name"]
        else:
            # Quito no está en dim_destinations → sin srch_destination_id.
            assert not hotel.get("srch_destination_id")
            assert hotel["city"] == "Quito"


def test_description_mirrored_to_hotel_content_pages(db, _geo_fixtures):
    seed(db)
    for entry in FEATURED_GEO:
        page = db.hotel_content_pages.find_one({"prop_id": entry["prop_id"]})
        assert page is not None and page["description"] == entry["description"]


def test_seed_is_idempotent(db, _geo_fixtures):
    first = seed(db)
    second = seed(db)
    assert first["created"] == 5
    assert second["created"] == 0
    assert db.dim_hotels.count_documents({"prop_id": {"$in": [1, 2, 3, 4, 5]}}) == 5


def test_seed_fails_when_visitor_country_missing(db, _geo_fixtures):
    # Quitamos Perú (219) de dim_visitor_countries → el seed debe abortar antes de escribir.
    db.dim_visitor_countries.delete_one({"visitor_location_country_id": 219})
    with pytest.raises(ValueError, match="219"):
        seed(db)
    assert db.dim_hotels.count_documents({}) == 0
