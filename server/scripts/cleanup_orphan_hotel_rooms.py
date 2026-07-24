"""Cleanup orphan hotel_room records that were incorrectly seeded from room types.

These records have IDs like HR-RT-{prop_id}-{room_type_slug} and were created
by seed scripts that auto-generated hotel_room entries for each room_type.
They should be room types, not physical hotel rooms.

Usage:
    python scripts/cleanup_orphan_hotel_rooms.py --prop_id 1   # dry-run
    python scripts/cleanup_orphan_hotel_rooms.py --prop_id 1 --apply  # actually delete

Without --prop_id, scans all properties.
"""

from __future__ import annotations

import argparse
import re
from typing import Any

from src.database.connection import get_database

# Pattern: HR-RT-{prop_id}-{slug}
HR_RT_PATTERN = re.compile(r"^HR-RT-\d+-")


def find_orphan_rooms(prop_id: int | None = None) -> list[dict[str, Any]]:
    """Find hotel_room records that have HR-RT- IDs (created from room type slugs)."""
    db = get_database()
    query: dict[str, Any] = {"hotel_room_id": {"$regex": r"^HR-RT-"}}
    if prop_id:
        query["prop_id"] = prop_id
    return list(db.hotel_rooms.find(query, {"_id": 0}).sort([("room_label", 1)]))


def delete_orphan_rooms(prop_id: int | None = None) -> int:
    """Delete orphan hotel_room records. Returns count of deleted documents."""
    db = get_database()
    query: dict[str, Any] = {"hotel_room_id": {"$regex": r"^HR-RT-"}}
    if prop_id:
        query["prop_id"] = prop_id
    result = db.hotel_rooms.delete_many(query)
    return result.deleted_count


def main():
    parser = argparse.ArgumentParser(description="Cleanup orphan hotel_rooms created from room types")
    parser.add_argument("--prop_id", type=int, default=None, help="Property ID to clean (default: all)")
    parser.add_argument("--apply", action="store_true", help="Actually delete (default: dry-run only)")
    args = parser.parse_args()

    print(f"{'='*60}")
    print("  Cleanup Orphan Hotel Rooms")
    print(f"  Mode: {'APPLY (will delete)' if args.apply else 'DRY-RUN (no changes)'}")
    if args.prop_id:
        print(f"  Property: {args.prop_id}")
    else:
        print("  Property: ALL")
    print(f"{'='*60}")

    orphans = find_orphan_rooms(args.prop_id)

    if not orphans:
        print("\n✅ No orphan HR-RT- rooms found. Nothing to clean up.")
        return

    print(f"\n📋 Found {len(orphans)} orphan room(s):")
    print(f"  {'ID':<45} {'N°':<6} {'Label':<25} {'Type':<30}")
    print(f"  {'-'*45} {'-'*6} {'-'*25} {'-'*30}")
    for room in orphans:
        print(
            f"  {room.get('hotel_room_id',''):<45} "
            f"{room.get('room_label',''):<6} "
            f"{(room.get('room_label') or ''):<25} "
            f"{room.get('room_type_id',''):<30}"
        )

    if args.apply:
        deleted = delete_orphan_rooms(args.prop_id)
        print(f"\n🗑️  Deleted {deleted} orphan room(s) from hotel_rooms.")
    else:
        print("\n⚠️  Dry-run mode. Run with --apply to actually delete.")
        print("   Example: python scripts/cleanup_orphan_hotel_rooms.py --prop_id 1 --apply")


if __name__ == "__main__":
    main()
