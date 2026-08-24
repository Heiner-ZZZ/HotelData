"""TDD: contrato del seed de hoteles reales (``scripts/seed_real_hotels.py``).

Fija el comportamiento del dataset de 15 hoteles reales mexicanos:

- Cada hotel se crea en ``dim_hotels`` con los campos que el perfil y las
  hotel-cards consumen (nombre, descripción, rating, coordenadas, moneda…).
- La relación geográfica es SIEMPRE contra las tablas del DATASET: país
  ``dim_visitor_countries`` (``prop_country_id`` = 148 México) y ciudad
  ``dim_destinations`` (``srch_destination_id``). Opción B: el hotel NO lleva
  campos del catálogo curado (``geo_country_code``/``geo_catalog_id``/
  ``geo_city_*``).
- Las coordenadas del hotel caen cerca del centro de su ciudad.
- La descripción se espeja a ``hotel_content_pages`` (fuente canónica de
  la descripción larga, igual que el flujo ``save_partner_hotel_profile``).
- Idempotente: una segunda pasada no duplica ni pisa.
- Nunca pisa un hotel existente: si un ``prop_id`` reservado ya existe,
  aborta con error (no sobrescribe ETL/partner).
- Sin relaciones huérfanas: si un país/ciudad no existe en ``geo_catalog``,
  aborta antes de escribir nada.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest
from bson import ObjectId

from scripts.seed_real_hotels import FEATURED_HOTELS, seed

# País y ciudades EXISTENTES de geo_catalog (misma forma que dev).
MX_COUNTRY = {"type": "country", "code": "MX", "name": "México", "iso_code": "MEX"}

# País México en dim_visitor_countries (tabla de países del dataset, FK legacy
# de dim_hotels.prop_country_id).
VISITOR_COUNTRY_MEXICO = {
    "visitor_location_country_id": 148,
    "country_name": "México",
    "country_display_name": "México",
    "visitor_country_label": "México",
}

# Destinos canónicos (nombre exacto, sin sufijo numérico) en dim_destinations.
# OJO: Puerto Vallarta y San José del Cabo NO existen en dim_destinations
# (solo en geo_catalog) — el seed debe dejar su srch_destination_id vacío.
VISITOR_DESTINATIONS = [
    {"srch_destination_id": 311, "destination_name": "Cancún"},
    {"srch_destination_id": 303, "destination_name": "Ciudad de México"},
    {"srch_destination_id": 304, "destination_name": "Guadalajara"},
    {"srch_destination_id": 305, "destination_name": "Monterrey"},
    {"srch_destination_id": 316, "destination_name": "Mérida"},
    {"srch_destination_id": 351, "destination_name": "Oaxaca"},
    {"srch_destination_id": 308, "destination_name": "Puebla"},
    {"srch_destination_id": 331, "destination_name": "Tijuana"},
    {"srch_destination_id": 344, "destination_name": "Veracruz"},
    {"srch_destination_id": 353, "destination_name": "Acapulco"},
]

MX_CITIES = [
    {"type": "city", "code": "ACA", "name": "Acapulco", "country_code": "MX", "state_code": "GRO", "latitude": 16.8531, "longitude": -99.8237},
    {"type": "city", "code": "CUN", "name": "Cancún", "country_code": "MX", "state_code": "QROO", "latitude": 21.1619, "longitude": -86.8515},
    {"type": "city", "code": "CDMX", "name": "Ciudad de México", "country_code": "MX", "state_code": "CDMX", "latitude": 19.4326, "longitude": -99.1332},
    {"type": "city", "code": "GDL", "name": "Guadalajara", "country_code": "MX", "state_code": "JAL", "latitude": 20.6597, "longitude": -103.3496},
    {"type": "city", "code": "MTY", "name": "Monterrey", "country_code": "MX", "state_code": "NL", "latitude": 25.6866, "longitude": -100.3161},
    {"type": "city", "code": "MID", "name": "Mérida", "country_code": "MX", "state_code": "YUC", "latitude": 20.9673, "longitude": -89.6236},
    {"type": "city", "code": "OAX", "name": "Oaxaca", "country_code": "MX", "state_code": "OAX", "latitude": 17.0732, "longitude": -96.7266},
    {"type": "city", "code": "PUEBLA", "name": "Puebla", "country_code": "MX", "state_code": "PUE", "latitude": 19.0414, "longitude": -98.2063},
    {"type": "city", "code": "PVR", "name": "Puerto Vallarta", "country_code": "MX", "state_code": "JAL", "latitude": 20.6534, "longitude": -105.2253},
    {"type": "city", "code": "SJD", "name": "San José del Cabo", "country_code": "MX", "state_code": "BCS", "latitude": 23.0642, "longitude": -109.6910},
    {"type": "city", "code": "TIJUANA", "name": "Tijuana", "country_code": "MX", "state_code": "BC", "latitude": 32.5149, "longitude": -117.0382},
    {"type": "city", "code": "VER", "name": "Veracruz", "country_code": "MX", "state_code": "VER", "latitude": 19.1738, "longitude": -96.1342},
]


@pytest.fixture(autouse=True)
def _geo_catalog(db):
    """Siembra las tablas geográficas que el seed resuelve (idénticas a dev).

    - ``geo_catalog``: país MX + ciudades (catálogo curado).
    - ``dim_visitor_countries``: país México=148 (tabla de países del dataset).
    - ``dim_destinations``: destinos canónicos (tabla de ciudades del dataset).

    ``geo_catalog`` no está en TEST_COLLECTIONS; ``dim_visitor_countries`` y
    ``dim_destinations`` sí se limpian por test, así que aquí se siembran.
    """
    db.geo_catalog.delete_many({})
    db.geo_catalog.insert_one(MX_COUNTRY)
    db.geo_catalog.insert_many(MX_CITIES)
    db.dim_visitor_countries.delete_many({})
    db.dim_visitor_countries.insert_one(VISITOR_COUNTRY_MEXICO)
    db.dim_destinations.delete_many({})
    db.dim_destinations.insert_many(VISITOR_DESTINATIONS)
    return db


def _city_center(db, code: str) -> dict:
    return db.geo_catalog.find_one({"type": "city", "code": code})


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def test_seed_creates_15_hotels_with_required_fields(db, _geo_catalog):
    stats = seed(db)

    assert stats["created"] == 15
    assert stats["skipped"] == 0

    hotels = list(db.dim_hotels.find({"prop_id": {"$in": [h["prop_id"] for h in FEATURED_HOTELS]}}))
    assert len(hotels) == 15

    for hotel in hotels:
        assert hotel["prop_id"] >= 900000
        assert hotel.get("display_name")
        assert hotel.get("hotel_name")
        assert hotel.get("hotel_label")
        assert hotel.get("description"), f"prop {hotel['prop_id']} sin descripción"
        assert hotel.get("city")
        assert hotel.get("address")
        assert hotel.get("active") is True
        assert hotel.get("currency") == "MXN"
        assert "MXN" in hotel.get("accepted_currencies", [])
        assert hotel.get("prop_starrating") in (3, 4, 5)
        assert hotel.get("prop_review_score", 0) > 0
        assert hotel.get("latitude") is not None
        assert hotel.get("longitude") is not None
        assert -90 <= hotel["latitude"] <= 90
        assert -180 <= hotel["longitude"] <= 180
        # Metadata de hotel "curado" (no generado por ETL)
        assert hotel.get("manual_override") is True
        assert hotel.get("name_source") == "manual"


def test_hotels_have_no_geo_catalog_relation(db, _geo_catalog):
    """Opción B: el hotel NO lleva relación al catálogo curado (geo_catalog).

    El país se resuelve solo por ``prop_country_id`` → ``dim_visitor_countries``
    y la ciudad por ``srch_destination_id`` → ``dim_destinations`` (o texto).
    Los campos ``geo_country_code``/``geo_catalog_id``/``geo_city_*`` deben
    estar AUSENTES del documento.
    """
    seed(db)

    for entry in FEATURED_HOTELS:
        hotel = db.dim_hotels.find_one({"prop_id": entry["prop_id"]})
        for field in ("geo_country_code", "geo_catalog_id", "geo_city_code", "geo_city_id"):
            assert field not in hotel, f"prop {entry['prop_id']} aún tiene {field}"
        assert hotel["prop_country_id"] == 148  # México en dim_visitor_countries
        assert hotel["display_country_label"] == "México"


def test_hotels_relate_to_visitor_country_and_destination(db, _geo_catalog):
    """El hotel se vincula a las tablas del dataset: país → dim_visitor_countries
    y ciudad → dim_destinations (srch_destination_id). Los hoteles cuya ciudad no
    existe en dim_destinations (Puerto Vallarta, San José del Cabo) NO llevan
    srch_destination_id."""
    mx = db.dim_visitor_countries.find_one({"visitor_location_country_id": 148})
    assert mx is not None
    seed(db)

    for entry in FEATURED_HOTELS:
        hotel = db.dim_hotels.find_one({"prop_id": entry["prop_id"]})
        # País del dataset (FK legacy) — debe existir en dim_visitor_countries.
        assert hotel["prop_country_id"] == mx["visitor_location_country_id"]
        assert hotel["display_country_label"] == mx["country_name"]

        if entry["destination"]:
            dest = db.dim_destinations.find_one({"srch_destination_id": hotel["srch_destination_id"]})
            assert dest is not None, f"prop {entry['prop_id']}: srch_destination_id no resuelve a dim_destinations"
            assert dest["destination_name"] == entry["destination"]
            assert hotel["city"] == entry["destination"]
        else:
            assert not hotel.get("srch_destination_id"), (
                f"prop {entry['prop_id']}: {entry['geo_city_code']} no está en dim_destinations "
                "y no debe tener srch_destination_id"
            )


def test_hotel_coordinates_near_city_center(db, _geo_catalog):
    seed(db)
    for entry in FEATURED_HOTELS:
        city = _city_center(db, entry["geo_city_code"])
        hotel = db.dim_hotels.find_one({"prop_id": entry["prop_id"]})
        dist = _haversine_km(
            hotel["latitude"], hotel["longitude"],
            city["latitude"], city["longitude"],
        )
        assert dist < 60, (
            f"prop {entry['prop_id']} ({entry['display_name']}) a {dist:.1f} km "
            f"del centro de {city['name']} — coordenada no aproximada"
        )


def test_description_mirrored_to_hotel_content_pages(db, _geo_catalog):
    seed(db)
    for entry in FEATURED_HOTELS:
        page = db.hotel_content_pages.find_one({"prop_id": entry["prop_id"]})
        assert page is not None, f"sin hotel_content_pages para prop {entry['prop_id']}"
        assert page.get("description"), f"hotel_content_pages vacío para prop {entry['prop_id']}"
        hotel = db.dim_hotels.find_one({"prop_id": entry["prop_id"]})
        assert page["description"] == hotel["description"]


def test_seed_is_idempotent(db, _geo_catalog):
    first = seed(db)
    before = db.dim_hotels.count_documents({"prop_id": {"$gte": 900000, "$lt": 901000}})

    second = seed(db)
    after = db.dim_hotels.count_documents({"prop_id": {"$gte": 900000, "$lt": 901000}})

    assert after == before == 15
    assert second["created"] == 0
    assert first["created"] == 15


def test_seed_refuses_to_overwrite_existing_hotel(db, _geo_catalog):
    db.dim_hotels.insert_one(
        {
            "prop_id": FEATURED_HOTELS[0]["prop_id"],
            "hotel_name": "Hotel ETL existente",
            "display_name": "Hotel ETL existente",
        }
    )
    with pytest.raises(ValueError, match="ya existe"):
        seed(db)


def test_seed_fails_when_visitor_country_missing(db, _geo_catalog):
    """Si México (148) no existe en dim_visitor_countries, el seed aborta
    ANTES de escribir (sin relaciones huérfanas de país)."""
    db.dim_visitor_countries.delete_one({"visitor_location_country_id": 148})

    with pytest.raises(ValueError, match="148"):
        seed(db)

    assert db.dim_hotels.count_documents({"prop_id": {"$gte": 900000}}) == 0
