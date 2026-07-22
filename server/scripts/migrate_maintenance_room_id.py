"""Backfill room_id (hotel_room_id) on legacy maintenance_tasks documents.

Usage (inside server container):
    python scripts/migrate_maintenance_room_id.py

The script iterates over maintenance_tasks that either:
  - don't have a room_id field, or
  - have a room_id equal to "" (empty string).

For each document, it looks up the corresponding hotel_rooms record by
prop_id + room_label (or room_number fallback) and sets room_id to the
hotel_room_id value.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Make src/ importable when running from repo root or scripts/ directory
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database.connection import get_database  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def migrate_maintenance_room_id(dry_run: bool = False) -> dict:
    db = get_database()
    collection = db["maintenance_tasks"]

    query = {
        "$or": [
            {"room_id": {"$exists": False}},
            {"room_id": None},
            {"room_id": ""},
        ]
    }

    total = collection.count_documents(query)
    logger.info("Found %d maintenance_tasks without room_id", total)

    updated = 0
    skipped = 0
    cursor = collection.find(query, {"_id": 1, "prop_id": 1, "room_label": 1, "room_number": 1})

    for doc in cursor:
        prop_id = doc.get("prop_id")
        room_label = doc.get("room_label") or ""
        room_number = doc.get("room_number") or ""

        if not prop_id or not room_label:
            logger.warning("Skipping doc %s: missing prop_id or room_label", doc["_id"])
            skipped += 1
            continue

        # Try exact room_label match first, then room_number fallback
        room_query: dict = {"prop_id": prop_id, "$or": []}
        if room_label:
            room_query["$or"].append({"room_label": room_label})
        if room_number:
            room_query["$or"].append({"room_number": room_number})

        if not room_query["$or"]:
            skipped += 1
            continue

        room = db["hotel_rooms"].find_one(
            room_query,
            {"_id": 0, "hotel_room_id": 1},
        )

        if not room or not room.get("hotel_room_id"):
            logger.warning(
                "Could not resolve hotel_room_id for maintenance_task %s (prop_id=%s, room_label=%s)",
                doc["_id"], prop_id, room_label,
            )
            skipped += 1
            continue

        hotel_room_id = room["hotel_room_id"]
        if dry_run:
            logger.info("[DRY-RUN] Would update %s with room_id=%s", doc["_id"], hotel_room_id)
            updated += 1
            continue

        collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"room_id": hotel_room_id}},
        )
        updated += 1

    return {"total": total, "updated": updated, "skipped": skipped}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backfill room_id in maintenance_tasks")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be updated without modifying data")
    args = parser.parse_args()

    result = migrate_maintenance_room_id(dry_run=args.dry_run)
    logger.info("Migration finished: %s", result)
