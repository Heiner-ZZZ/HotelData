"""Migrate hotel_id ObjectId FK for 6 core transactional collections.

Backfills ``hotel_id`` (ObjectId FK → dim_hotels._id) for collections that
only had ``prop_id`` as an integer dimension key.

Idempotent — skips docs that already have a valid ObjectId in ``hotel_id``.

Collections:
  booking_orders, guest_folios, stay_sessions, stay_service_requests,
  reservation_invoices, reservation_payments
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")
from datetime import datetime, timezone

from src.database.connection import get_database

COLLECTIONS = [
    "booking_orders",
    "guest_folios",
    "stay_sessions",
    "stay_service_requests",
    "reservation_invoices",
    "reservation_payments",
]


def _build_lookup(db) -> dict[int, object]:
    """Build a prop_id → _id lookup from dim_hotels."""
    lookup: dict[int, object] = {}
    for doc in db.dim_hotels.find({}, {"prop_id": 1}):
        pid = doc.get("prop_id")
        if pid is not None:
            lookup[int(pid)] = doc["_id"]
    return lookup


def main() -> None:
    db = get_database()

    lookup = _build_lookup(db)
    print(f"dim_hotels lookup: {len(lookup)} entries")

    grand_total = 0

    for coll_name in COLLECTIONS:
        coll = db[coll_name]

        # Count docs needing migration: have prop_id, no hotel_id ObjectId
        needing = coll.count_documents({
            "prop_id": {"$exists": True},
            "$or": [
                {"hotel_id": {"$exists": False}},
                {"hotel_id": {"$type": "string"}},  # legacy string FK also fixed
            ],
        })

        if needing == 0:
            print(f"\n[{coll_name}] ✅ All {coll.count_documents({})} docs already have hotel_id ObjectId")
            continue

        print(f"\n[{coll_name}] {needing} of {coll.count_documents({})} docs need hotel_id backfill")

        updated = 0
        skipped = 0

        cursor = coll.find(
            {
                "prop_id": {"$exists": True},
                "$or": [
                    {"hotel_id": {"$exists": False}},
                    {"hotel_id": {"$type": "string"}},
                ],
            },
            {"prop_id": 1},
        )

        for doc in cursor:
            prop_id = doc.get("prop_id")
            if prop_id is None:
                skipped += 1
                continue

            hotel_oid = lookup.get(int(prop_id))
            if hotel_oid is None:
                skipped += 1
                continue

            coll.update_one(
                {"_id": doc["_id"]},
                {"$set": {"hotel_id": hotel_oid, "_migrated_hotel_id_at": datetime.now(timezone.utc)}},
            )
            updated += 1

        print(f"  Updated: {updated}  |  Skipped (no dim_hotels match): {skipped}")
        grand_total += updated

    print(f"\n{'='*50}")
    print(f"TOTAL backfilled: {grand_total} docs across 6 collections")


if __name__ == "__main__":
    main()
