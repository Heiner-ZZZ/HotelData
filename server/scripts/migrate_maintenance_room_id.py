"""Backfill room_id (ObjectId FK) and hotel_room_id on legacy maintenance_tasks.

Idempotent: resolves room_label/room_number against hotel_rooms and sets:
  - room_id       → hotel_rooms._id (ObjectId FK)
  - hotel_room_id → hotel_rooms.hotel_room_id (string, denormalized)
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

    # Catch docs missing hotel_room_id (regardless of room_id content)
    query = {
        "$or": [
            {"hotel_room_id": {"$exists": False}},
            {"hotel_room_id": None},
            {"hotel_room_id": ""},
            {"room_id": {"$type": "string"}},
        ]
    }

    total = collection.count_documents(query)
    logger.info("Found %d maintenance_tasks without room_id", total)

    updated = 0
    skipped = 0
    cursor = collection.find(query, {"_id": 1, "prop_id": 1, "room_label": 1})

    for doc in cursor:
        try:
            prop_id = doc.get("prop_id")
            room_label = doc.get("room_label") or ""

            if not prop_id or not room_label:
                logger.warning("Skipping doc %s: missing prop_id or room_label", doc["_id"])
                skipped += 1
                continue

            # Try exact room_label match
            room_query: dict = {"prop_id": prop_id, "$or": []}
            if room_label:
                room_query["$or"].append({"room_label": room_label})

            if not room_query["$or"]:
                skipped += 1
                continue

            # Also try resolving by existing room_id string (e.g. "HR-1-101")
            existing_room_id = doc.get("room_id")
            if existing_room_id and isinstance(existing_room_id, str) and existing_room_id:
                room_query["$or"].append({"hotel_room_id": existing_room_id})

            room = db["hotel_rooms"].find_one(
                room_query,
                {"_id": 1, "hotel_room_id": 1},
            )

            if not room or not room.get("hotel_room_id"):
                logger.warning(
                    "Could not resolve hotel_room_id for maintenance_task %s (prop_id=%s, room_label=%s)",
                    doc["_id"], prop_id, room_label,
                )
                skipped += 1
                continue

            hotel_room_id = room["hotel_room_id"]
            room_object_id = room["_id"]
            if dry_run:
                logger.info("[DRY-RUN] Would update %s with room_id=%s, hotel_room_id=%s", doc["_id"], room_object_id, hotel_room_id)
                updated += 1
                continue

            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"room_id": room_object_id, "hotel_room_id": hotel_room_id}},
            )
            updated += 1
        except Exception as exc:
            logger.exception("Failed to migrate maintenance_task %s: %s", doc.get("_id"), exc)
            skipped += 1

    return {"total": total, "updated": updated, "skipped": skipped}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backfill room_id in maintenance_tasks")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be updated without modifying data")
    args = parser.parse_args()

    result = migrate_maintenance_room_id(dry_run=args.dry_run)
    logger.info("Migration finished: %s", result)
