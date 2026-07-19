"""Seed global amenity price defaults into hotel_content_pages (prop_id=0).

Usage:
    docker compose -f infra/docker-compose.yml exec server python scripts/seed_amenity_price_defaults.py
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.connection import get_database

GLOBAL_DEFAULTS_PROP_ID = 0

DEFAULT_PRICES = {
    "desayuno incluido": 15.0, "desayuno": 15.0,
    "camas extra": 25.0, "cama extra": 25.0,
    "cunas": 15.0, "cuna": 15.0,
    "parking": 20.0, "estacionamiento": 20.0,
    "minibar": 15.0, "caja fuerte": 5.0,
    "spa": 40.0, "masajes": 50.0, "masaje": 50.0, "sauna": 25.0,
    "servicio a la habitacion": 12.0, "servicio a la habitación": 12.0,
    "cafe": 5.0, "café": 5.0, "bar": 8.0, "restaurante": 0.0,
    "gimnasio": 10.0, "mascotas": 30.0, "mascota": 30.0, "pet friendly": 30.0,
    "lavandería": 18.0, "lavanderia": 18.0, "laundry": 18.0,
    "late check-out": 35.0, "late checkout": 35.0,
    "traslado al aeropuerto": 35.0, "shuttle gratuito": 0.0, "shuttle": 0.0,
    "valet parking": 25.0, "alquiler de auto": 45.0,
    "alquiler de bicicletas": 10.0, "bicicletas": 10.0,
    "transporte privado": 60.0, "taxi": 15.0,
}


def seed() -> None:
    db = get_database()
    now = datetime.now(timezone.utc)

    db.hotel_content_pages.update_one(
        {"prop_id": GLOBAL_DEFAULTS_PROP_ID},
        {
            "$set": {
                "amenity_prices": DEFAULT_PRICES,
                "updated_at": now,
                "updated_by": "seed_script",
            },
            "$setOnInsert": {"prop_id": GLOBAL_DEFAULTS_PROP_ID, "created_at": now},
        },
        upsert=True,
    )

    count = len(DEFAULT_PRICES)
    print(f"Seeded {count} global amenity price defaults into hotel_content_pages (prop_id={GLOBAL_DEFAULTS_PROP_ID}).")

    # Clean up the old separate collection if it exists
    if "amenity_price_defaults" in db.list_collection_names():
        db.drop_collection("amenity_price_defaults")
        print("Cleaned up old 'amenity_price_defaults' collection.")


if __name__ == "__main__":
    seed()
