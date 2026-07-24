"""Remove redundant fields from 3 collections.

Idempotent — safe to run multiple times.

Collections:
  room_status_log   — remove room_number (== room_label, 48 docs)
  hotel_rooms       — remove room_number (== room_label, 48 docs)
  employees         — remove position_name (== position, 5 docs)
"""
from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from src.database.connection import get_database  # noqa: E402


def _unset_if_all_equal(db, coll_name: str, field: str, compare_field: str) -> int:
    """Unset `field` from all docs in `coll_name` if it always equals `compare_field`."""
    coll = db[coll_name]
    total = coll.count_documents({field: {"$exists": True}})
    if total == 0:
        print(f"  {coll_name}: nothing to clean (0 docs with {field})")
        return 0

    mismatched = coll.count_documents({
        compare_field: {"$exists": True},
        field: {"$exists": True},
        "$expr": {"$ne": ["$" + compare_field, "$" + field]},
    })
    if mismatched > 0:
        print(f"  {coll_name}: SKIPPED — {mismatched} docs have {compare_field} != {field}")
        return 0

    result = coll.update_many(
        {field: {"$exists": True}},
        {"$unset": {field: ""}},
    )
    print(f"  {coll_name}: removed {field} from {result.modified_count} / {total} docs")
    return result.modified_count


def main():
    db = get_database()

    print("=== employees: position_name ===")
    _unset_if_all_equal(db, "employees", "position_name", "position")

    print("\n=== room_status_log: room_number ===")
    _unset_if_all_equal(db, "room_status_log", "room_number", "room_label")

    print("\n=== hotel_rooms: room_number ===")
    _unset_if_all_equal(db, "hotel_rooms", "room_number", "room_label")

    print("\nDone.")


if __name__ == "__main__":
    main()
