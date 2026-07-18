"""Seed script to populate the geo_catalog collection with countries, states, and cities.

Run: python -m server.scripts.seed_data.seed_geo_catalog

Requires MongoDB running.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient, errors


load_dotenv()

GEO_COLLECTION = "geo_catalog"

COUNTRIES = [
    {"code": "MX", "name": "México", "iso_code": "MEX"},
    {"code": "US", "name": "Estados Unidos", "iso_code": "USA"},
    {"code": "ES", "name": "España", "iso_code": "ESP"},
    {"code": "AR", "name": "Argentina", "iso_code": "ARG"},
    {"code": "CO", "name": "Colombia", "iso_code": "COL"},
    {"code": "CL", "name": "Chile", "iso_code": "CHL"},
    {"code": "PE", "name": "Perú", "iso_code": "PER"},
    {"code": "BR", "name": "Brasil", "iso_code": "BRA"},
    {"code": "CA", "name": "Canadá", "iso_code": "CAN"},
    {"code": "GB", "name": "Reino Unido", "iso_code": "GBR"},
    {"code": "DE", "name": "Alemania", "iso_code": "DEU"},
    {"code": "FR", "name": "Francia", "iso_code": "FRA"},
    {"code": "IT", "name": "Italia", "iso_code": "ITA"},
    {"code": "JP", "name": "Japón", "iso_code": "JPN"},
    {"code": "CN", "name": "China", "iso_code": "CHN"},
]

MEXICO_STATES = [
    {"code": "AGS", "name": "Aguascalientes"},
    {"code": "BC", "name": "Baja California"},
    {"code": "BCS", "name": "Baja California Sur"},
    {"code": "CAMP", "name": "Campeche"},
    {"code": "CHIS", "name": "Chiapas"},
    {"code": "CHIH", "name": "Chihuahua"},
    {"code": "CDMX", "name": "Ciudad de México"},
    {"code": "COAH", "name": "Coahuila"},
    {"code": "COL", "name": "Colima"},
    {"code": "DGO", "name": "Durango"},
    {"code": "GTO", "name": "Guanajuato"},
    {"code": "GRO", "name": "Guerrero"},
    {"code": "HGO", "name": "Hidalgo"},
    {"code": "JAL", "name": "Jalisco"},
    {"code": "MEX", "name": "Estado de México"},
    {"code": "MICH", "name": "Michoacán"},
    {"code": "MOR", "name": "Morelos"},
    {"code": "NAY", "name": "Nayarit"},
    {"code": "NL", "name": "Nuevo León"},
    {"code": "OAX", "name": "Oaxaca"},
    {"code": "PUE", "name": "Puebla"},
    {"code": "QRO", "name": "Querétaro"},
    {"code": "QROO", "name": "Quintana Roo"},
    {"code": "SLP", "name": "San Luis Potosí"},
    {"code": "SIN", "name": "Sinaloa"},
    {"code": "SON", "name": "Sonora"},
    {"code": "TAB", "name": "Tabasco"},
    {"code": "TAMPS", "name": "Tamaulipas"},
    {"code": "TLAX", "name": "Tlaxcala"},
    {"code": "VER", "name": "Veracruz"},
    {"code": "YUC", "name": "Yucatán"},
    {"code": "ZAC", "name": "Zacatecas"},
]

# Major Mexican cities with coordinates
MEXICO_CITIES = [
    {"code": "CDMX", "name": "Ciudad de México", "state": "CDMX", "lat": 19.4326, "lng": -99.1332},
    {"code": "GDL", "name": "Guadalajara", "state": "JAL", "lat": 20.6597, "lng": -103.3496},
    {"code": "MTY", "name": "Monterrey", "state": "NL", "lat": 25.6866, "lng": -100.3161},
    {"code": "CUN", "name": "Cancún", "state": "QROO", "lat": 21.1619, "lng": -86.8515},
    {"code": "PVR", "name": "Puerto Vallarta", "state": "JAL", "lat": 20.6534, "lng": -105.2253},
    {"code": "MID", "name": "Mérida", "state": "YUC", "lat": 20.9673, "lng": -89.6236},
    {"code": "PUEBLA", "name": "Puebla", "state": "PUE", "lat": 19.0414, "lng": -98.2063},
    {"code": "TIJUANA", "name": "Tijuana", "state": "BC", "lat": 32.5149, "lng": -117.0382},
    {"code": "SJD", "name": "San José del Cabo", "state": "BCS", "lat": 23.0642, "lng": -109.6910},
    {"code": "ZIH", "name": "Zihuatanejo", "state": "GRO", "lat": 17.6417, "lng": -101.5523},
    {"code": "ACA", "name": "Acapulco", "state": "GRO", "lat": 16.8531, "lng": -99.8237},
    {"code": "QRO", "name": "Querétaro", "state": "QRO", "lat": 20.5888, "lng": -100.3899},
    {"code": "SLP", "name": "San Luis Potosí", "state": "SLP", "lat": 22.1498, "lng": -100.9792},
    {"code": "MORE", "name": "Morelia", "state": "MICH", "lat": 19.7021, "lng": -101.1917},
    {"code": "CHIH", "name": "Chihuahua", "state": "CHIH", "lat": 28.6353, "lng": -106.0889},
    {"code": "HER", "name": "Hermosillo", "state": "SON", "lat": 29.0892, "lng": -110.9613},
    {"code": "VER", "name": "Veracruz", "state": "VER", "lat": 19.1738, "lng": -96.1342},
    {"code": "CAMP", "name": "Campeche", "state": "CAMP", "lat": 19.8301, "lng": -90.5349},
    {"code": "VSA", "name": "Villahermosa", "state": "TAB", "lat": 17.9892, "lng": -92.9474},
    {"code": "OAX", "name": "Oaxaca", "state": "OAX", "lat": 17.0732, "lng": -96.7266},
]


def get_db():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DATABASE", "hoteldata_hub")
    client = MongoClient(uri)
    client.admin.command("ping")
    return client[db_name]


def upsert_geo(db, entry: dict) -> int:
    now = datetime.now(timezone.utc)
    doc = {
        **entry,
        "is_active": True,
        "created_at": now,
        "updated_at": None,
    }
    try:
        result = db[GEO_COLLECTION].update_one(
            {"type": entry["type"], "code": entry["code"]},
            {"$setOnInsert": doc},
            upsert=True,
        )
        return 1 if result.upserted_id else 0
    except errors.DuplicateKeyError:
        return 0


def main():
    db = get_db()
    inserted = 0

    # Countries
    for c in COUNTRIES:
        inserted += upsert_geo(db, {
            "type": "country", "code": c["code"], "name": c["name"],
            "iso_code": c["iso_code"],
        })
    print(f"Countries: {inserted} inserted (total: {len(COUNTRIES)})")

    # Mexican states
    state_count = 0
    for s in MEXICO_STATES:
        state_count += upsert_geo(db, {
            "type": "state", "code": s["code"], "name": s["name"],
            "country_code": "MX",
        })
    print(f"States: {state_count} inserted (total: {len(MEXICO_STATES)})")

    # Mexican cities
    city_count = 0
    for c in MEXICO_CITIES:
        city_count += upsert_geo(db, {
            "type": "city", "code": c["code"], "name": c["name"],
            "country_code": "MX", "state_code": c["state"],
            "latitude": c["lat"], "longitude": c["lng"],
        })
    print(f"Cities: {city_count} inserted (total: {len(MEXICO_CITIES)})")

    total = db[GEO_COLLECTION].count_documents({})
    by_type = list(db[GEO_COLLECTION].aggregate([
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]))
    print(f"\nTotal in geo_catalog: {total}")
    for t in by_type:
        print(f"  {t['_id']}: {t['count']}")


if __name__ == "__main__":
    main()
