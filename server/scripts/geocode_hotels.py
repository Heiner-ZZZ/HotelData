"""Backfill de geolocalización: geocodifica direcciones de ``dim_hotels`` sin lat/lng.

Usa el servicio ``geocoding`` (Nominatim + caché Mongo + rate-limit ≤1 req/s).
Idempotente: los hoteles que ya tienen coordenadas se omiten; los que no
tienen DIRECCIÓN (solo ciudad) también se omiten — el ETL cae a ``geo_catalog``
para la coordenada de ciudad. Se ejecuta dentro del contenedor server:

    python scripts/geocode_hotels.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.app.modules.geocoding.service import geocode
from src.database.connection import get_database


def _missing_coords() -> dict:
    return {
        "$or": [
            {"latitude": None},
            {"latitude": {"$exists": False}},
            {"longitude": None},
            {"longitude": {"$exists": False}},
        ]
    }


def main() -> int:
    db = get_database()
    candidates = list(
        db.dim_hotels.find(
            _missing_coords(),
            {"prop_id": 1, "city": 1, "display_country_label": 1, "address": 1},
        )
    )

    resolved = 0
    skipped_no_address = 0
    failed = 0
    for hotel in candidates:
        address = str(hotel.get("address") or "").strip()
        if not address:
            skipped_no_address += 1
            continue
        result = geocode(
            address,
            city=str(hotel.get("city") or ""),
            country=str(hotel.get("display_country_label") or ""),
        )
        if not result:
            failed += 1
            print(f"  ✗ prop {hotel['prop_id']}: sin resultado para «{address}»")
            continue
        db.dim_hotels.update_one(
            {"_id": hotel["_id"]},
            {"$set": {"latitude": result["latitude"], "longitude": result["longitude"]}},
        )
        resolved += 1
        print(
            f"  ✓ prop {hotel['prop_id']}: «{address}» → "
            f"({result['latitude']}, {result['longitude']})"
        )

    print(
        f"\nBackfill geocoding terminado: {resolved} resueltos, "
        f"{skipped_no_address} sin dirección (omitidos), {failed} sin resolver."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
