"""
Migrate dim_hotels: composite indexes for the similar-hotels prefilter.

The public endpoint /api/hotels/{prop_id}/similar ranks candidates with
`dim_hotels.find({prop_id: {$ne}, <country field>: X, prop_starrating: <rango>})
.sort({prop_review_score: -1}).limit(30)`. Without a composite index the
planner falls back to `IXSCAN prop_id_1` + blocking SORT and examines the
WHOLE catalog (93,990 docs) to return a handful of candidates.

These two indexes let the planner narrow by country first (equality prefix),
so the scan touches only the source country's hotels (tens, not tens of
thousands) before the star range and the review-score top-k.

Idempotent: create_index is a no-op when the index already exists.

Usage:
    docker compose -f infra/docker-compose.yml exec server python scripts/migrate_dim_hotels_similar_indexes.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/app")

from pymongo import ASCENDING, DESCENDING, MongoClient

from config.settings import get_settings

INDEXES = [
    # Path legacy: prop_country_id (todos los hoteles lo tienen).
    ([("prop_country_id", ASCENDING), ("prop_starrating", ASCENDING), ("prop_review_score", DESCENDING)], "idx_dim_hotels_country_star_review"),
    # Path geo: geo_country_code (la mayoría de los hoteles migrados).
    ([("geo_country_code", ASCENDING), ("prop_starrating", ASCENDING), ("prop_review_score", DESCENDING)], "idx_dim_hotels_geo_star_review"),
]


def main() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]
    print(f"Creando índices de similares en dim_hotels ({settings.mongo_database})...")
    for keys, name in INDEXES:
        try:
            created = db.dim_hotels.create_index(keys, name=name)
            print(f"  → {created} listo.")
        except Exception as exc:  # noqa: BLE001 - idempotente: ya existía
            print(f"  → {name}: {exc}")
    print("Listo. Verifica con explain(): el plan debe usar el índice y examinar solo el país.")
    client.close()


if __name__ == "__main__":
    main()
