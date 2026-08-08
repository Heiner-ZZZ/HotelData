"""Backfill ``shift_id`` ObjectId FK into booking_orders, guest_folios, reservation_payments.

Links each document to the reception shift whose time window covers its
``created_at`` / ``paid_at`` timestamp — the same matching rule the
close-of-shift snapshot uses (``_collect_related_ids`` in
``reception/shifts.py``), but written as a live FK on the documents
themselves so future reconciliation is FK-driven instead of window-guessed.

Front-desk-only rule:
  - ``booking_orders`` whose ``booking_source`` is a web channel
    (``web_request``, ``booking_engine``, OTAs, etc.) are SKIPPED — web
    reservations are never tied to a cash shift.
  - ``guest_folios`` and ``reservation_payments`` are always front-desk
    artifacts in this system, so they are linked whenever their timestamp
    falls inside a shift window.

Idempotent: only documents whose ``shift_id`` is missing/empty are
considered. Safe to run multiple times.

Usage:
    docker compose -f infra/docker-compose.yml exec server \
        python scripts/migrate_shift_id_backfill.py --dry-run
    docker compose -f infra/docker-compose.yml exec server \
        python scripts/migrate_shift_id_backfill.py
"""

from __future__ import annotations

import argparse
import sys

sys.path.insert(0, "/app")

from datetime import datetime, timezone  # noqa: E402

from bson import ObjectId  # noqa: E402
from src.database.connection import get_database  # noqa: E402

RECEPTION_SHIFTS_COLLECTION = "reception_shifts"

# Booking channels that must NEVER be tied to a cash shift. Front-desk /
# manual / role-based sources fall through and get backfilled.
WEB_CHANNEL_SOURCES = frozenset({
    "web_request",
    "web",
    "booking_engine",
    "direct",
    "direct_website",
    "ota",
    "booking.com",
    "expedia",
    "cliente",
})

# (collection, timestamp field, label)
TARGETS = [
    ("booking_orders", "created_at", "bookings"),
    ("guest_folios", "created_at", "folios"),
    ("reservation_payments", "paid_at", "payments"),
]


def _parse_ts(value) -> datetime | None:
    """Parse an ISO string or datetime into a tz-aware datetime, or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _shift_windows(db) -> list[tuple[ObjectId, datetime, datetime]]:
    """Return [(shift_id, start, end)] for every shift, oldest first."""
    windows: list[tuple[ObjectId, datetime, datetime]] = []
    for doc in db[RECEPTION_SHIFTS_COLLECTION].find({}, {"start_time": 1, "closed_at": 1, "status": 1}):
        start = _parse_ts(doc.get("start_time"))
        if start is None:
            continue
        end = _parse_ts(doc.get("closed_at"))
        if end is None:
            end = datetime.now(timezone.utc)  # still-open shift
        windows.append((doc["_id"], start, end))
    windows.sort(key=lambda w: w[1])
    return windows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be backfilled without writing anything.",
    )
    args = parser.parse_args()

    db = get_database()
    windows = _shift_windows(db)
    print(f"reception_shifts windows: {len(windows)} shifts")

    grand_total = 0
    for coll_name, ts_field, label in TARGETS:
        coll = db[coll_name]
        total = coll.count_documents({})
        needing = coll.count_documents(
            {"$or": [{"shift_id": {"$exists": False}}, {"shift_id": None}]}
        )
        print(f"\n[{coll_name}] {needing} of {total} docs need shift_id backfill")
        if needing == 0:
            continue

        updated = 0
        skipped = 0
        cursor = coll.find(
            {"$or": [{"shift_id": {"$exists": False}}, {"shift_id": None}]},
            {"_id": 1, ts_field: 1, "booking_source": 1},
        )
        for doc in cursor:
            if coll_name == "booking_orders":
                source = (doc.get("booking_source") or "").strip().lower()
                if source in WEB_CHANNEL_SOURCES:
                    skipped += 1
                    continue

            ts = _parse_ts(doc.get(ts_field))
            if ts is None:
                skipped += 1
                continue

            matched: ObjectId | None = None
            for shift_id, start, end in windows:
                if start <= ts <= end:
                    matched = shift_id
                    break
            if matched is None:
                skipped += 1
                continue

            if not args.dry_run:
                coll.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {
                        "shift_id": matched,
                        "_migrated_shift_id_at": datetime.now(timezone.utc),
                    }},
                )
            updated += 1

        verb = "WOULD update" if args.dry_run else "Updated"
        print(f"  {verb}: {updated}  |  Skipped (no window / web source / bad ts): {skipped}")
        grand_total += updated

    print(f"\n{'=' * 50}")
    if args.dry_run:
        print(f"DRY-RUN — no writes performed. TOTAL that would be backfilled: {grand_total}")
    else:
        print(f"TOTAL backfilled: {grand_total} docs across {len(TARGETS)} collections")


if __name__ == "__main__":
    main()
