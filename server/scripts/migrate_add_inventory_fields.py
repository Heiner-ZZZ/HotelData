"""Backfill inventory traceability fields in hotel_products.

Adds the following fields to existing docs that don't have them yet (idempotent):
  - type:                  "retail" (default; pivot to "supply" / "asset" in UI)
  - cost_price:            0.0
  - default_supplier:      None
  - supplier_sku:          None
  - par_level:             None
  - last_purchase_invoice_ref: None
  - last_purchase_at:      None
  - last_purchase_qty:     None
  - archived_at:           None
  - archived_by:           None
  - updated_by:            None

Run: docker compose -f infra/docker-compose.yml exec -T server python scripts/migrate_add_inventory_fields.py

Safe to re-run; uses $exists filters.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/app")

from datetime import datetime, timezone

from src.database.connection import get_database


COLLECTION = "hotel_products"

# Field, default-value pairs to backfill. Each adds the field only if missing.
NEW_FIELDS: dict[str, object] = {
    "type": "retail",
    "cost_price": 0.0,
    "default_supplier": None,
    "supplier_sku": None,
    "par_level": None,
    "last_purchase_invoice_ref": None,
    "last_purchase_at": None,
    "last_purchase_qty": None,
    "archived_at": None,
    "archived_by": None,
    "updated_by": None,
}


def main() -> None:
    db = get_database()
    coll = db[COLLECTION]

    total = coll.count_documents({})
    print(f"[hotel_products] total docs: {total}")

    if total == 0:
        print("[hotel_products] empty collection — nothing to backfill")
        return

    grand_updated = 0

    for field, default in NEW_FIELDS.items():
        # Idempotency: only update docs that don't yet have the field.
        result = coll.update_many(
            {field: {"$exists": False}},
            {"$set": {field: default}},
        )
        modified = result.modified_count
        grand_updated += modified
        print(
            f"  +{field:>32}  = {default!r:<22}  →  {modified} doc(s) updated"
        )

    print(f"\n{'='*60}")
    print(f"TOTAL field updates: {grand_updated}")
    print(f"Migration completed at: {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
