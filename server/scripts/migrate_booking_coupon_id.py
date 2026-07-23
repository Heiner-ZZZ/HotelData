"""Link existing booking_orders to coupon_codes via coupon_id FK.

Idempotent: only updates bookings with a coupon_code but without coupon_id.
Matches coupon_code string against coupon_codes.coupon_code (case-insensitive
since booking_codes are stored uppercase and catalog codes may vary).
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

from src.database.connection import get_database  # noqa: E402


def migrate() -> None:
    db = get_database()

    # Build coupon_code → _id lookup
    print("Building coupon_code → _id lookup...")
    code_to_id: dict[str, object] = {}
    for cc in db.coupon_codes.find({}, {"coupon_code": 1}):
        code = (cc.get("coupon_code") or "").strip().upper()
        if code:
            code_to_id[code] = cc["_id"]
    print(f"  → {len(code_to_id)} coupon codes mapped.")

    # Find bookings with coupon_code but without coupon_id
    query = {
        "coupon_code": {"$exists": True, "$ne": "", "$ne": None},
        "$or": [
            {"coupon_id": {"$exists": False}},
            {"coupon_id": None},
            {"coupon_id": ""},
        ],
    }

    bookings = list(db.booking_orders.find(query, {"_id": 1, "booking_id": 1, "coupon_code": 1}))
    print(f"\nBookings needing migration: {len(bookings)}")

    updated = 0
    skipped: list[str] = []

    for bk in bookings:
        bid = bk["_id"]
        code = (bk.get("coupon_code") or "").strip().upper()
        coupon_id = code_to_id.get(code)

        if coupon_id:
            db.booking_orders.update_one(
                {"_id": bid},
                {"$set": {"coupon_id": coupon_id}},
            )
            updated += 1
        else:
            skipped.append(f"{bk.get('booking_id', '?')}: coupon_code={code!r} not in catalog")

    print(f"\nDone: {updated}/{len(bookings)} migrated.")
    if skipped:
        print(f"Skipped {len(skipped)}:")
        for s in skipped:
            print(f"  - {s}")


if __name__ == "__main__":
    migrate()
