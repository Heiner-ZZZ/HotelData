"""Migrate employees.position (free-text) → position_id (FK to employee_positions._id).

Idempotent: only updates employees missing position_id.
Denormalizes position_name from the matched catalog entry.
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from src.database.connection import get_database  # noqa: E402


def migrate() -> None:
    db = get_database()
    collection = db["employees"]
    positions_coll = db["employee_positions"]

    # Build lookup: position name → _id
    position_map: dict[str, object] = {}
    for doc in positions_coll.find({}, {"name": 1}):
        name = doc.get("name", "")
        if name:
            position_map[name] = doc["_id"]

    print(f"Catálogo employee_positions: {len(position_map)} puestos")
    for name, oid in position_map.items():
        print(f"  {name} → {oid}")

    # Find employees missing position_id
    query = {
        "$or": [
            {"position_id": {"$exists": False}},
            {"position_id": None},
        ]
    }
    total = collection.count_documents(query)
    print(f"\nEmpleados sin position_id: {total}")

    if total == 0:
        print("Nada que migrar.")
        return

    updated = 0
    skipped = 0

    for emp in collection.find(query, {"_id": 1, "position": 1, "full_name": 1}):
        eid = emp["_id"]
        position = (emp.get("position") or "").strip()

        if not position:
            print(f"  SKIP {eid} ({emp.get('full_name', '?')}): position vacío")
            skipped += 1
            continue

        position_id = position_map.get(position)
        if not position_id:
            print(f"  SKIP {eid} ({emp.get('full_name', '?')}): position={position!r} no está en el catálogo")
            skipped += 1
            continue

        collection.update_one(
            {"_id": eid},
            {"$set": {
                "position_id": position_id,
            }},
        )
        updated += 1
        print(f"  OK {eid} ({emp.get('full_name', '?')}): {position} → {position_id}")

    print(f"\nMigración completada: {updated} updated, {skipped} skipped")


if __name__ == "__main__":
    migrate()
