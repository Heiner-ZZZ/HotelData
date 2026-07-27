"""Backfill ``fact_inventory`` with ``opening_stock`` layers.

Fase 6 introduces the ``fact_inventory`` collection that powers FIFO/LIFO
COGS accounting. Products that existed BEFORE this migration have
``quantity_available > 0`` but no layer rows. Without this backfill,
``compute_cogs_report`` would fall back to ``hotel_products.cost_price``
for every drain, making the FIFO/LIFO ordering irrelevant — the report
would return numbers identical to ``method=approx``.

This script:
  1. Lists all hotel_products with ``quantity_available > 0`` and no
     matching layer in ``fact_inventory``.
  2. Inserts ONE opening_stock layer per such product with:
       - ``qty_remaining`` = ``quantity_available`` snapshot
       - ``cost_per_unit`` = ``cost_price`` snapshot
       - ``acquired_at``  = ``product.created_at`` if available, else now
       - ``source``       = ``"opening_stock"``
       - ``created_by``   = ``"migration:fase6"``
       - ``layer_id``     = ``"INV-OPENING-{token_hex(4).upper()}"`` (sentinel pattern)
  3. Marks each inserted layer with ``metadata.migration_id`` so it can be
     distinguished from a real restock and audited end-to-end.

Idempotency:
  - The script checks for product_id existence in ``fact_inventory`` before
    inserting, so re-running is safe.
  - Running multiple times does NOT create duplicate layers per product.

Scope:
  - Filters to ``prop_id`` range (default: all real hotel prop_ids, i.e.
    ``>= 1``); skips ``prop_id < 1`` (zip / test fixtures).
  - Mark non-real test fixtures via ``seed_source`` exclusion if desired
    (script accepts ``--skip-seed-source <name>``).

Run: python /app/scripts/migrate_inventory_layers.py [--dry-run] [--skip-seed-source <name>]
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.app.modules.partner.services._inventory import (
    insert_inventory_layer,
)
from src.app.modules.partner.services._common import now_utc
from src.database.connection import get_database


# Sentinel prefix for the human-readable ``layer_id`` so opening_stock layers
# can be visually distinguished from restocks (``INV-A1B2C3D4``) without
# needing to query the ``source`` field.
OPENING_LAYER_PREFIX = "INV-OPENING-"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def list_products_needing_backfill(
    db: Any,
    *,
    skip_seed_source: str | None = None,
    only_prop_id: int | None = None,
) -> list[dict[str, Any]]:
    """Return products with ``quantity_available > 0`` and no layer.

    Filter ``is_active=True``, ``archived_at=None``, ``quantity_available > 0``.
    Exclude products that already have ANY non-archived layer (``qty_remaining > 0``
    OR ``qty_remaining`` = 0 but ``is_active=True`` represents an unconsumed layer
    which we shouldn't double-write).
    """
    # Real hotel prop_ids: always >= 1. The seed script seeds prop_id 1..5.
    prop_filter: dict[str, Any] = {"$gte": 1} if only_prop_id is None else only_prop_id

    products = list(
        db.hotel_products.find(
            {
                "prop_id": prop_filter,
                "is_active": True,
                "archived_at": None,
                "quantity_available": {"$gt": 0},
            },
            {
                "_id": 0,
                "prop_id": 1,
                "product_id": 1,
                "name": 1,
                "cost_price": 1,
                "quantity_available": 1,
                "created_at": 1,
                "created_by": 1,
                "default_supplier": 1,
                "seed_source": 1,
            },
        )
    )

    if skip_seed_source:
        products = [p for p in products if p.get("seed_source") != skip_seed_source]

    # Filter out products that already have any active layer.
    missing: list[dict[str, Any]] = []
    for p in products:
        existing = db.fact_inventory.find_one(
            {
                "prop_id": p["prop_id"],
                "product_id": p["product_id"],
                "is_active": True,
            },
            {"_id": 1},
        )
        if existing is None:
            missing.append(p)
    return missing


def backfill_one(
    db: Any,
    product: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    """Insert an opening_stock layer for ``product``. Returns a summary dict."""
    prop_id = int(product["prop_id"])
    product_id = str(product["product_id"])
    qty = float(product.get("quantity_available", 0))
    cost = float(product.get("cost_price", 0.0) or 0.0)
    created_at = product.get("created_at")
    acquired_at = (
        created_at if isinstance(created_at, datetime) else now_utc()
    )

    if dry_run:
        return {
            "prop_id": prop_id,
            "product_id": product_id,
            "name": product.get("name", ""),
            "qty": qty,
            "cost_per_unit": round(cost, 2),
            "acquired_at": (
                acquired_at.isoformat() if isinstance(acquired_at, datetime) else None
            ),
            "would_insert_layer": True,
        }

    doc = insert_inventory_layer(
        prop_id=prop_id,
        product_id=product_id,
        qty=qty,
        cost_per_unit=cost,
        source="opening_stock",
        supplier_name=product.get("default_supplier", "") or "",
        invoice_ref="",  # No invoice ref for backfilled opening stock
        acquired_at=acquired_at,
        created_by="migration:fase6",
    )

    # Sentinel layer_id overrides the random one in insert_inventory_layer.
    sentinel_layer_id = f"{OPENING_LAYER_PREFIX}{secrets.token_hex(4).upper()}"
    db.fact_inventory.update_one(
        {"_id": doc["_id"]},
        {"$set": {"layer_id": sentinel_layer_id, "metadata.migration_id": "fase6"}},
    )

    return {
        "prop_id": prop_id,
        "product_id": product_id,
        "name": product.get("name", ""),
        "qty": qty,
        "cost_per_unit": round(cost, 2),
        "layer_id": sentinel_layer_id,
        "acquired_at": acquired_at.isoformat() if isinstance(acquired_at, datetime) else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill fact_inventory with opening_stock layers (Fase 6)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List products that would be backfilled without inserting.",
    )
    parser.add_argument(
        "--skip-seed-source",
        default=None,
        help="Exclude products with this seed_source (e.g. 'seed_hotel_products').",
    )
    parser.add_argument(
        "--only-prop-id",
        type=int,
        default=None,
        help="Restrict to a single prop_id (useful for staging).",
    )
    args = parser.parse_args(argv)

    db = get_database()
    candidates = list_products_needing_backfill(
        db,
        skip_seed_source=args.skip_seed_source,
        only_prop_id=args.only_prop_id,
    )

    action = "would_insert" if args.dry_run else "inserted"
    summaries: list[dict[str, Any]] = []
    for p in candidates:
        summaries.append(backfill_one(db, p, dry_run=args.dry_run))

    print(
        json.dumps(
            {
                "candidates_count": len(candidates),
                "dry_run": args.dry_run,
                "skip_seed_source": args.skip_seed_source,
                "only_prop_id": args.only_prop_id,
                "action": action,
                "items": summaries,
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )
    print(
        f"{'🛈 Would insert' if args.dry_run else '✅ Inserted'}: "
        f"{len(summaries)} opening_stock layer(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
