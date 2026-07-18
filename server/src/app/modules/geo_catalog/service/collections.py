"""Collections and indexes for the geographic catalog module."""

from __future__ import annotations

from datetime import datetime, timezone

from pymongo import ASCENDING, IndexModel

from src.database.collections import ensure_collection
from src.database.connection import get_database

GEO_COLLECTION = "geo_catalog"

GEO_INDEXES = [
    IndexModel([("type", ASCENDING)], name="idx_geo_type"),
    IndexModel([("code", ASCENDING)], name="idx_geo_code"),
    IndexModel([("country_code", ASCENDING)], name="idx_geo_country"),
    IndexModel([("state_code", ASCENDING)], name="idx_geo_state"),
    IndexModel([("type", ASCENDING), ("code", ASCENDING)], name="idx_geo_type_code", unique=True),
    IndexModel([("name", ASCENDING)], name="idx_geo_name"),
]

# Default seed data: countries, Mexican states, and major cities
_DEFAULT_SEED = [
    # Countries
    {"type": "country", "code": "MX", "name": "México", "iso_code": "MEX"},
    {"type": "country", "code": "US", "name": "Estados Unidos", "iso_code": "USA"},
    {"type": "country", "code": "ES", "name": "España", "iso_code": "ESP"},
    {"type": "country", "code": "AR", "name": "Argentina", "iso_code": "ARG"},
    {"type": "country", "code": "CO", "name": "Colombia", "iso_code": "COL"},
    {"type": "country", "code": "CL", "name": "Chile", "iso_code": "CHL"},
    {"type": "country", "code": "PE", "name": "Perú", "iso_code": "PER"},
    {"type": "country", "code": "BR", "name": "Brasil", "iso_code": "BRA"},
    {"type": "country", "code": "CA", "name": "Canadá", "iso_code": "CAN"},
    # Mexican states
    {"type": "state", "code": "CDMX", "name": "Ciudad de México", "country_code": "MX"},
    {"type": "state", "code": "JAL", "name": "Jalisco", "country_code": "MX"},
    {"type": "state", "code": "NL", "name": "Nuevo León", "country_code": "MX"},
    {"type": "state", "code": "QROO", "name": "Quintana Roo", "country_code": "MX"},
    {"type": "state", "code": "YUC", "name": "Yucatán", "country_code": "MX"},
    {"type": "state", "code": "BC", "name": "Baja California", "country_code": "MX"},
    {"type": "state", "code": "BCS", "name": "Baja California Sur", "country_code": "MX"},
    {"type": "state", "code": "GRO", "name": "Guerrero", "country_code": "MX"},
    {"type": "state", "code": "MICH", "name": "Michoacán", "country_code": "MX"},
    {"type": "state", "code": "OAX", "name": "Oaxaca", "country_code": "MX"},
    {"type": "state", "code": "PUE", "name": "Puebla", "country_code": "MX"},
    {"type": "state", "code": "VER", "name": "Veracruz", "country_code": "MX"},
    # Major Mexican cities
    {"type": "city", "code": "CDMX", "name": "Ciudad de México", "country_code": "MX", "state_code": "CDMX", "latitude": 19.4326, "longitude": -99.1332},
    {"type": "city", "code": "GDL", "name": "Guadalajara", "country_code": "MX", "state_code": "JAL", "latitude": 20.6597, "longitude": -103.3496},
    {"type": "city", "code": "MTY", "name": "Monterrey", "country_code": "MX", "state_code": "NL", "latitude": 25.6866, "longitude": -100.3161},
    {"type": "city", "code": "CUN", "name": "Cancún", "country_code": "MX", "state_code": "QROO", "latitude": 21.1619, "longitude": -86.8515},
    {"type": "city", "code": "MID", "name": "Mérida", "country_code": "MX", "state_code": "YUC", "latitude": 20.9673, "longitude": -89.6236},
    {"type": "city", "code": "PVR", "name": "Puerto Vallarta", "country_code": "MX", "state_code": "JAL", "latitude": 20.6534, "longitude": -105.2253},
    {"type": "city", "code": "ACA", "name": "Acapulco", "country_code": "MX", "state_code": "GRO", "latitude": 16.8531, "longitude": -99.8237},
    {"type": "city", "code": "OAX", "name": "Oaxaca", "country_code": "MX", "state_code": "OAX", "latitude": 17.0732, "longitude": -96.7266},
    {"type": "city", "code": "PUEBLA", "name": "Puebla", "country_code": "MX", "state_code": "PUE", "latitude": 19.0414, "longitude": -98.2063},
    {"type": "city", "code": "VER", "name": "Veracruz", "country_code": "MX", "state_code": "VER", "latitude": 19.1738, "longitude": -96.1342},
    {"type": "city", "code": "TIJUANA", "name": "Tijuana", "country_code": "MX", "state_code": "BC", "latitude": 32.5149, "longitude": -117.0382},
    {"type": "city", "code": "SJD", "name": "San José del Cabo", "country_code": "MX", "state_code": "BCS", "latitude": 23.0642, "longitude": -109.6910},
]


def ensure_geo_collections() -> None:
    db = get_database()
    ensure_collection(GEO_COLLECTION, GEO_INDEXES)
    # Auto-seed if collection is empty
    if db[GEO_COLLECTION].estimated_document_count() == 0:  # type: ignore[index]
        now = datetime.now(timezone.utc)
        for entry in _DEFAULT_SEED:
            doc = {**entry, "is_active": True, "created_at": now, "updated_at": None}
            db[GEO_COLLECTION].update_one(
                {"type": entry["type"], "code": entry["code"]},
                {"$setOnInsert": doc},
                upsert=True,
            )
        import logging
        logging.getLogger(__name__).info("Seeded geo_catalog with %d default entries", len(_DEFAULT_SEED))
