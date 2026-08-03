"""Normalize operational Mongo documents used by the operations KPI.

This script is intentionally separate from the ETL and does not run on import.
It resolves legacy ``room_label`` records against ``hotel_rooms`` and only copies
metadata when an explicit source alias exists. It never invents timestamps,
 supplier countries or weights.

Examples:
  python scripts/migrate_operations_consistency.py --dry-run
  python scripts/migrate_operations_consistency.py --prop-id 1 --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database.connection import get_database  # noqa: E402

ROOM_COLLECTIONS = (
    "housekeeping_tasks",
    "maintenance_tasks",
    "room_status_log",
    "room_status_history",
)


def _room_query(doc: dict[str, Any]) -> dict[str, Any] | None:
    prop_id = doc.get("prop_id")
    if not prop_id:
        return None
    candidates: list[dict[str, Any]] = []
    label = str(doc.get("room_label") or doc.get("room_number") or "").strip()
    existing = doc.get("hotel_room_id") or doc.get("room_id")
    if label:
        candidates.append({"room_label": label})
    if isinstance(existing, str) and existing.strip():
        candidates.append({"hotel_room_id": existing.strip()})
    return {"prop_id": prop_id, "$or": candidates} if candidates else None


def _room_update(doc: dict[str, Any], room: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "room_id": room["_id"],
        "hotel_room_id": room.get("hotel_room_id", ""),
        "room_label": room.get("room_label") or doc.get("room_label", ""),
        "room_type_id": room.get("room_type_id", doc.get("room_type_id", "")),
    }
    if room.get("floor") is not None:
        fields["floor"] = room["floor"]
    return fields


def _metadata_alias_update(doc: dict[str, Any]) -> dict[str, Any]:
    """Return only explicit aliases; absent source values remain absent."""
    update: dict[str, Any] = {}
    if not doc.get("supplier_country"):
        value = doc.get("supplier_country_code") or doc.get("country_of_supplier")
        if value:
            update["supplier_country"] = str(value).strip()
    if doc.get("weight") is None:
        value = doc.get("package_weight") or doc.get("net_weight")
        if value is not None:
            try:
                update["weight"] = float(value)
            except (TypeError, ValueError):
                pass
    if not doc.get("weight_unit"):
        value = doc.get("package_weight_unit") or doc.get("unit_of_weight")
        if value:
            update["weight_unit"] = str(value).strip()
    return update


def migrate(*, prop_id: int | None = None, apply: bool = False) -> dict[str, Any]:
    db = get_database()
    room_filter = {"prop_id": prop_id} if prop_id else {}
    rooms = list(db.hotel_rooms.find(room_filter, {"_id": 1, "prop_id": 1, "hotel_room_id": 1, "room_label": 1, "room_type_id": 1, "floor": 1}))
    by_label = {(r.get("prop_id"), str(r.get("room_label"))): r for r in rooms if r.get("room_label")}
    by_hotel_id = {(r.get("prop_id"), str(r.get("hotel_room_id"))): r for r in rooms if r.get("hotel_room_id")}

    result: dict[str, Any] = {"apply": apply, "room_collections": {}, "inventory": {"scanned": 0, "updated": 0, "missing_metadata": 0}}
    for collection_name in ROOM_COLLECTIONS:
        collection = db[collection_name]
        query: dict[str, Any] = {"prop_id": prop_id} if prop_id else {}
        stats = {"scanned": 0, "updated": 0, "unresolved": 0}
        for doc in collection.find(query):
            stats["scanned"] += 1
            prop = doc.get("prop_id")
            label = str(doc.get("room_label") or doc.get("room_number") or "")
            candidate = by_label.get((prop, label)) or by_hotel_id.get((prop, str(doc.get("hotel_room_id") or doc.get("room_id") or "")))
            if not candidate:
                stats["unresolved"] += 1
                continue
            update = _room_update(doc, candidate)
            changed = any(doc.get(key) != value for key, value in update.items())
            if changed:
                stats["updated"] += 1
                if apply:
                    collection.update_one({"_id": doc["_id"]}, {"$set": update})
        result["room_collections"][collection_name] = stats

    inventory = db.fact_inventory
    inventory_query: dict[str, Any] = {}
    inventory_stats = result["inventory"]
    for doc in inventory.find(inventory_query, {"supplier_country": 1, "supplier_country_code": 1, "country_of_supplier": 1, "weight": 1, "package_weight": 1, "net_weight": 1, "weight_unit": 1, "package_weight_unit": 1, "unit_of_weight": 1}):
        inventory_stats["scanned"] += 1
        aliases = _metadata_alias_update(doc)
        if aliases:
            inventory_stats["updated"] += 1
            if apply:
                inventory.update_one({"_id": doc["_id"]}, {"$set": aliases})
        if not (doc.get("supplier_country") or aliases.get("supplier_country")) or doc.get("weight") is None and "weight" not in aliases:
            inventory_stats["missing_metadata"] += 1

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize operations Mongo documents safely")
    parser.add_argument("--prop-id", type=int, default=None)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Report changes without writing (default)")
    mode.add_argument("--apply", action="store_true", help="Persist only deterministic canonical/alias updates")
    args = parser.parse_args()
    result = migrate(prop_id=args.prop_id, apply=args.apply)
    print(result)


if __name__ == "__main__":
    main()
