"""Seed the canonical manual-payment methods into ``payment_methods`` (idempotent).

Single source of truth: ``DEFAULT_PAYMENT_METHODS`` in
``src/app/modules/subscriptions/payment_methods.py``
(`docs/PLAN_SUSCRIPCION_Y_PAGOS.md` §5.1/§7).

Semántica del upsert: cada método se inserta si falta o se actualiza con
``$set`` al valor canónico (nunca ``delete_many``). Los ``details`` (banco,
titular, número de cuenta) los edita el admin en la BD; re-correr el seed los
refresca al canónico.

Usage:
    docker compose --env-file .env -f infra/docker-compose.yml exec -T server \\
        python scripts/seed_payment_methods.py            # escribe
    docker compose --env-file .env -f infra/docker-compose.yml exec -T server \\
        python scripts/seed_payment_methods.py --dry-run  # solo reporta
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

sys.path.insert(0, "/app")

from src.app.modules.subscriptions.payment_methods import DEFAULT_PAYMENT_METHODS


def seed_payment_methods(db, *, dry_run: bool = False) -> dict[str, int]:
    """Upsert idempotente del catálogo canónico en ``payment_methods``."""
    now = datetime.now(UTC)
    inserted = 0
    updated = 0
    for method in DEFAULT_PAYMENT_METHODS:
        code = method["code"]
        exists = db.payment_methods.find_one({"code": code}, {"_id": 1})
        if exists:
            if not dry_run:
                db.payment_methods.update_one(
                    {"code": code},
                    {"$set": {**method, "is_active": True, "updated_at": now}},
                )
            updated += 1
        else:
            if not dry_run:
                db.payment_methods.insert_one(
                    {**method, "is_active": True, "created_at": now, "updated_at": now}
                )
            inserted += 1
    return {
        "inserted": inserted,
        "updated": updated,
        "total": db.payment_methods.count_documents({}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed payment_methods from the canonical payment-method catalog."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report what would change without writing."
    )
    args = parser.parse_args()

    from pymongo import MongoClient

    from config.settings import get_settings

    settings = get_settings()
    client: MongoClient = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]
    result = seed_payment_methods(db, dry_run=args.dry_run)
    print(
        f"Inserted: {result['inserted']}, Updated: {result['updated']}, "
        f"Total in payment_methods: {result['total']}"
    )
    client.close()
    print("Done.")


if __name__ == "__main__":
    main()
