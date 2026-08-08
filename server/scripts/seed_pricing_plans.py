"""Seed the canonical pricing bands into ``pricing_plans`` (idempotent).

Single source of truth: ``DEFAULT_PRICING_PLANS`` in
``src/app/modules/property_approval/pricing.py``
(`docs/APROBACION_HOTELES_Y_PRICING.md` §6 — bandas recalibradas a valores de
adopción amigable + descuento por pago anual).

Semántica del upsert: cada banda se inserta si falta o se actualiza con
``$set`` al valor canónico si ya existe (nunca ``delete_many`` — la colección
es el catálogo ajustable del admin). Ojo: re-correr el script refresca los
precios al catálogo canónico; los ajustes manuales del admin viven en la
colección hasta el siguiente seed.

Usage:
    docker compose -f infra/docker-compose.yml exec server \
        python scripts/seed_pricing_plans.py            # escribe
    docker compose -f infra/docker-compose.yml exec server \
        python scripts/seed_pricing_plans.py --dry-run  # solo reporta
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app")

from src.app.modules.property_approval.pricing import (
    DEFAULT_PRICING_PLANS,
)


def seed_pricing_plans(db, *, dry_run: bool = False) -> dict[str, int]:
    """Upsert idempotente del catálogo canónico en ``pricing_plans``.

    Returns: conteos ``{"inserted", "updated", "total"}`` (``total`` refleja
    el estado real de la colección; en dry-run no hay escrituras).
    """
    now = datetime.now(timezone.utc)
    inserted = 0
    updated = 0
    for plan in DEFAULT_PRICING_PLANS:
        band = int(plan["band"])
        exists = db.pricing_plans.find_one({"band": band}, {"_id": 1})
        if exists:
            if not dry_run:
                db.pricing_plans.update_one(
                    {"band": band},
                    {"$set": {**plan, "is_active": True, "updated_at": now}},
                )
            updated += 1
        else:
            if not dry_run:
                db.pricing_plans.insert_one(
                    {**plan, "is_active": True, "created_at": now, "updated_at": now}
                )
            inserted += 1
    return {
        "inserted": inserted,
        "updated": updated,
        "total": db.pricing_plans.count_documents({}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed pricing_plans from the canonical pricing catalog."
    )
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing.")
    args = parser.parse_args()

    from pymongo import MongoClient

    from config.settings import get_settings

    settings = get_settings()
    client: MongoClient = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]
    result = seed_pricing_plans(db, dry_run=args.dry_run)
    print(
        f"Inserted: {result['inserted']}, Updated: {result['updated']}, "
        f"Total in pricing_plans: {result['total']}"
    )
    client.close()
    print("Done.")


if __name__ == "__main__":
    main()
