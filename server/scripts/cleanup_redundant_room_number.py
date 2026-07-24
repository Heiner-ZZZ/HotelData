"""Remove redundant ``room_number`` field from collections where it always
equals ``room_label``.

Idempotent — safe to run multiple times.

Collections: housekeeping_tasks, guest_folios, stay_sessions, blackout_dates
"""
from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from src.database.connection import get_database  # noqa: E402

COLLECTIONS = [
    "housekeeping_tasks",
    "guest_folios",
    "stay_sessions",
    "blackout_dates",
]


def main():
    db = get_database()

    for coll_name in COLLECTIONS:
        coll = db[coll_name]
        total = coll.count_documents({"room_number": {"$exists": True}})
        if total == 0:
            print(f"  {coll_name}: nothing to clean (0 docs with room_number)")
            continue

        # Verify room_label == room_number for ALL docs before unsetting
        mismatched = coll.count_documents({
            "room_label": {"$exists": True},
            "room_number": {"$exists": True},
            "$expr": {"$ne": ["$room_label", "$room_number"]},
        })
        if mismatched > 0:
            print(f"  {coll_name}: SKIPPED — {mismatched} docs have room_label != room_number")
            continue

        result = coll.update_many(
            {"room_number": {"$exists": True}},
            {"$unset": {"room_number": ""}},
        )
        print(f"  {coll_name}: removed room_number from {result.modified_count} / {total} docs")

    print("\nDone.")


if __name__ == "__main__":
    main()
