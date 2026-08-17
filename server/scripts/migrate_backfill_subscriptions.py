"""Backfill subscriptions for hotels approved before the Fase 2 gate.

`docs/PLAN_SUSCRIPCION_Y_PAGOS.md` §13 Fase 2. Idempotent: approved hotels
with no subscription get an ``active`` subscription with band = ``price_band``
(or recomputed from ``total_rooms_declared`` when missing). Never touches
pending/rejected hotels. Safe to re-run — a second pass creates nothing.

Usage:
    docker compose --env-file .env -f infra/docker-compose.yml exec -T server \\
        python scripts/migrate_backfill_subscriptions.py            # escribe
    docker compose --env-file .env -f infra/docker-compose.yml exec -T server \\
        python scripts/migrate_backfill_subscriptions.py --dry-run  # solo reporta
"""

from __future__ import annotations

import argparse
import sys

sys.path.insert(0, "/app")

from src.app.modules.property_approval.pricing import suggested_band_for
from src.app.modules.subscriptions.service import (
    VALID_BANDS,
    create_subscription,
)
from src.database.connection import get_database

APPROVED = "approved"


def backfill_subscriptions(db, *, dry_run: bool = False) -> dict[str, int]:
    """Create an ``active`` subscription for each approved hotel without one."""
    created = 0
    skipped = 0
    for hotel in db.dim_hotels.find({"approval_status": APPROVED}):
        prop_id = hotel.get("prop_id")
        if prop_id is None:
            skipped += 1
            continue
        if db.subscriptions.find_one({"prop_id": prop_id}):
            skipped += 1  # ya backfilleado (idempotencia)
            continue

        band = hotel.get("price_band")
        if band not in VALID_BANDS:
            suggested = suggested_band_for(db, hotel.get("total_rooms_declared", 0))
            band = suggested.get("band") if suggested else None
        if band not in VALID_BANDS:
            skipped += 1
            continue

        if not dry_run:
            create_subscription(
                db,
                prop_id=int(prop_id),
                owner_user_id=hotel.get("owner_user_id"),
                band=int(band),
                billing_cycle="monthly",
                currency=hotel.get("currency", "USD"),
                initial_status="active",
            )
        created += 1
    return {"created": created, "skipped": skipped, "dry_run": dry_run}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill active subscriptions for approved hotels without one."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report what would change without writing."
    )
    args = parser.parse_args()

    db = get_database()
    result = backfill_subscriptions(db, dry_run=args.dry_run)
    print(
        f"Created: {result['created']}, Skipped: {result['skipped']}, "
        f"Dry run: {result['dry_run']}"
    )
    print("Done.")


if __name__ == "__main__":
    main()
