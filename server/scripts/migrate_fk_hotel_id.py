"""Migrate existing docs in 4 collections: prop_id (int) → hotel_id (ObjectId FK).

Run: docker compose -f infra/docker-compose.yml exec -T server python scripts/migrate_fk_hotel_id.py

Backfills:
- lost_and_found:       hotel_id, reported_by_id
- hotel_products:       hotel_id
- hotel_images:         hotel_id
- reception_shifts:     hotel_id, employee_id
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/app")

from config.settings import get_settings
from pymongo import MongoClient
from src.app.core.resolvers import resolve_hotel_id, resolve_employee_id


def main() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]

    stats: dict[str, int] = {}

    # ── lost_and_found ──────────────────────────────────────────────
    print("=== lost_and_found ===")
    updated = 0
    for doc in db.lost_and_found.find({"hotel_id": {"$exists": False}}):
        pid_raw = doc.get("prop_id")
        pid: int | None = None
        try:
            pid = int(pid_raw) if pid_raw is not None else None
        except (TypeError, ValueError):
            pass
        if pid is None:
            continue
        hotel_id = resolve_hotel_id(pid)
        updates: dict = {"hotel_id": hotel_id} if hotel_id else {}
        found_by = doc.get("found_by", "").strip()
        if found_by:
            emp_id = resolve_employee_id(found_by)
            if emp_id:
                updates["found_by_id"] = emp_id
        if updates:
            db.lost_and_found.update_one({"_id": doc["_id"]}, {"$set": updates})
            updated += 1
            print(f"  ✓ {doc.get('item_name', doc['_id'])} → hotel_id={hotel_id}")
    stats["lost_and_found"] = updated
    print(f"  Updated: {updated}")

    # ── hotel_products ──────────────────────────────────────────────
    print("\n=== hotel_products ===")
    updated = 0
    for doc in db.hotel_products.find({"hotel_id": {"$exists": False}}):
        pid_raw = doc.get("prop_id")
        pid: int | None = None
        try:
            pid = int(pid_raw) if pid_raw is not None else None
        except (TypeError, ValueError):
            pass
        if pid is None:
            continue
        hotel_id = resolve_hotel_id(pid)
        if hotel_id:
            db.hotel_products.update_one(
                {"_id": doc["_id"]}, {"$set": {"hotel_id": hotel_id}}
            )
            updated += 1
            print(f"  ✓ {doc.get('name', doc['_id'])} → hotel_id={hotel_id}")
    stats["hotel_products"] = updated
    print(f"  Updated: {updated}")

    # ── hotel_images ────────────────────────────────────────────────
    print("\n=== hotel_images ===")
    updated = 0
    for doc in db.hotel_images.find({"hotel_id": {"$exists": False}}):
        pid_raw = doc.get("prop_id")
        pid: int | None = None
        try:
            pid = int(pid_raw) if pid_raw is not None else None
        except (TypeError, ValueError):
            pass
        if pid is None:
            continue
        hotel_id = resolve_hotel_id(pid)
        if hotel_id:
            db.hotel_images.update_one(
                {"_id": doc["_id"]}, {"$set": {"hotel_id": hotel_id}}
            )
            updated += 1
            print(f"  ✓ {doc.get('image_url', doc['_id'])} → hotel_id={hotel_id}")
    stats["hotel_images"] = updated
    print(f"  Updated: {updated}")

    # ── reception_shifts ────────────────────────────────────────────
    print("\n=== reception_shifts ===")
    updated = 0
    for doc in db.reception_shifts.find({"hotel_id": {"$exists": False}}):
        pid_raw = doc.get("prop_id")
        pid: int | None = None
        try:
            pid = int(pid_raw) if pid_raw is not None else None
        except (TypeError, ValueError):
            pass
        if pid is None:
            continue
        hotel_id = resolve_hotel_id(pid)
        updates: dict = {"hotel_id": hotel_id} if hotel_id else {}
        emp_name = doc.get("employee", "").strip()
        if emp_name:
            emp_id = resolve_employee_id(emp_name)
            if emp_id:
                updates["employee_id"] = emp_id
        if updates:
            db.reception_shifts.update_one({"_id": doc["_id"]}, {"$set": updates})
            updated += 1
            print(
                f"  ✓ {doc.get('shift_type', doc['_id'])}"
                f" → hotel_id={hotel_id}, employee_id={updates.get('employee_id')}"
            )
    stats["reception_shifts"] = updated
    print(f"  Updated: {updated}")

    # ── Summary ─────────────────────────────────────────────────────
    print(f"\n{'='*50}")
    print("SUMMARY")
    for coll, cnt in stats.items():
        print(f"  {coll}: {cnt} updated")
    print(f"  TOTAL: {sum(stats.values())} docs migrated")

    client.close()


if __name__ == "__main__":
    main()
