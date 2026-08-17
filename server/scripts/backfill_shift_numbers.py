"""Backfill per-hotel per-day sequential shift numbers (T01, T02, ...).

One-shot migration for ``reception_shifts`` opened before ``shift_number``
existed (2026-08). Numbering rules mirror ``open_shift``:

* The counter is per ``prop_id`` per UTC calendar day of ``start_time``.
* Shifts are ordered by ``start_time`` ascending within the day; the
  N-th shift of that day gets ``N``.
* Idempotent: only documents whose stored number differs are updated.

Dry-run is the default; pass ``--apply`` to write:

    docker compose --env-file .env -f infra/docker-compose.yml exec -T server python scripts/backfill_shift_numbers.py
    docker compose --env-file .env -f infra/docker-compose.yml exec -T server python scripts/backfill_shift_numbers.py --apply
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database  # noqa: E402

RECEPTION_SHIFTS = "reception_shifts"


def _day_bucket(start_time) -> str:
    """UTC calendar day of a shift ``start_time`` (ISO string or datetime)."""
    if isinstance(start_time, datetime):
        dt = start_time
    else:
        try:
            dt = datetime.fromisoformat(str(start_time))
        except (TypeError, ValueError):
            return f"unknown:{str(start_time)[-12:] or '?'}"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    args = parser.parse_args()

    db = get_database()
    docs = list(db[RECEPTION_SHIFTS].find({}).sort([("prop_id", 1), ("start_time", 1)]))
    print(f"Total shifts: {len(docs)}")

    counters: dict[tuple[int, str], int] = {}
    updated = 0
    unchanged = 0
    for doc in docs:
        prop_id = int(doc.get("prop_id") or 0)
        bucket = _day_bucket(doc.get("start_time"))
        counters[(prop_id, bucket)] = counters.get((prop_id, bucket), 0) + 1
        number = counters[(prop_id, bucket)]
        current = doc.get("shift_number")
        if current == number:
            unchanged += 1
            continue
        if args.apply:
            db[RECEPTION_SHIFTS].update_one(
                {"_id": doc["_id"]},
                {"$set": {"shift_number": number}},
            )
        updated += 1
        print(f"  prop_id={prop_id} day={bucket} start={doc.get('start_time')} -> T{number:02d} (was {current})")

    mode = "APPLIED" if args.apply else "DRY-RUN (no writes)"
    print(f"\n{mode} — updates={updated} unchanged={unchanged} total={len(docs)}")


if __name__ == "__main__":
    main()
