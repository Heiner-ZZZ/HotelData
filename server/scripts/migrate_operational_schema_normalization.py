"""Normalize schema drift in day-to-day operational collections (2026-Q3).

Background (from the Mongo 27018 audit, 2026-08):
The project is mid-migration: several write paths now emit richer documents
(ObjectId FKs, extra fields) than the legacy/seed rows, and a few FK fields
were stored with the wrong BSON type for the CURRENT canonical write path.
This script only applies deterministic, idempotent ``$set`` backfills —
it never deletes, never invents values that cannot be resolved from a
source collection, and never touches ETL/dataset collections.

Fixes applied (each gated by an explicit source lookup):

1. ``booking_orders.user_id``  str → ObjectId
   ``booking_orders.user_id`` is a BSON ObjectId FK to ``users._id``,
   matching the rest of the codebase (reviews, user_sessions,
   role_assignments, …). The write path (``routes/reservations.py`` +
   ``validation.build_reservation_input``) and the client "mis reservas"
   filter (``queries.py``) now use ObjectId. Legacy hex-string rows are
   wrapped back into ``ObjectId``.

2. ``booking_orders.hotel_id`` backfill (missing rows)
   Canonical create writes ``hotel_id: resolve_hotel_id(prop_id)``
   (``lifecycle/create/core.py``). Backfill missing from ``dim_hotels``.

3. ``users.primary_role_id`` backfill
   Canonical user creation (auth register, admin ownership, HR) writes
   ``primary_role_id`` = roles._id. ``init_security_model_ga03.py`` only
   wrote ``primary_role``, so seeded users lack the FK that security
   checks prefer (``role_helpers``). Resolve from ``roles.role_name``.

4. ``users.email_verified`` → true (missing rows)
   Canonical register flow always sets it; the seed omitted it.

5. ``hotel_products.hotel_id`` backfill (missing rows)
   Canonical product create writes ``hotel_id: resolve_hotel_id(prop_id)``
   (``partner/services/hotel_products.py``); Fase 5 seed rows lack it.

6. ``room_types.hotel_id`` backfill (missing rows)
   Canonical room-type create writes it (``partner/services/rooms/types/_core.py``).

7. ``room_inventory_calendar`` ``is_deleted``/``version`` backfill
   Canonical write always sets ``is_deleted=False`` + ``version=1``
   (``partner/services/rooms/inventory.py``); optimistic-concurrency
   updates compare ``version``. Legacy rows lack both.

8. ``permissions`` ``created_at``/``updated_at``/``is_system`` backfill
   Two legacy ``crud.*`` rows lack the audit fields every other row has.

9. ``employees.user_id``  str → ObjectId
   FK to ``users._id``. Canonical write paths (``create_employee`` and
   ``_ensure_user_account`` in ``hr/routes.py``) now store the raw
   ``ObjectId``; ``my-portal`` and ``reception/shifts.py`` query by
   ObjectId. Legacy hex-string rows are wrapped back into ``ObjectId``.

10. ``employee_shifts.employee_id``  str → ObjectId
    FK to ``employees._id``, matching ``employee_documents.employee_id``
    and ``reception_shifts.employee_id``. ``hr/routes.py`` now stores and
    queries the ObjectId; legacy hex-string rows are wrapped back.

Examples:
  python scripts/migrate_operational_schema_normalization.py --dry-run
  python scripts/migrate_operational_schema_normalization.py --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bson import ObjectId

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database.connection import get_database  # noqa: E402

_HEX24_RE = re.compile(r"[0-9a-fA-F]{24}")


def _is_hex24(value: str) -> bool:
    return bool(_HEX24_RE.fullmatch(value))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _build_hotel_map(db) -> dict[int, ObjectId]:
    """prop_id → dim_hotels._id for every property referenced in the DB."""
    hotel_map: dict[int, ObjectId] = {}
    for doc in db.dim_hotels.find({"prop_id": {"$ne": None}}, {"prop_id": 1, "_id": 1}):
        pid = doc.get("prop_id")
        if isinstance(pid, int) and pid > 0:
            hotel_map[pid] = doc["_id"]
    return hotel_map


def _build_role_map(db) -> dict[str, ObjectId]:
    """role_name → roles._id."""
    return {
        doc["role_name"]: doc["_id"]
        for doc in db.roles.find({}, {"role_name": 1, "_id": 1})
        if doc.get("role_name")
    }


def migrate(*, apply: bool = False) -> dict[str, Any]:
    db = get_database()
    result: dict[str, Any] = {"apply": apply}
    hotel_map = _build_hotel_map(db)
    role_map = _build_role_map(db)

    # ── 1. booking_orders.user_id: str → ObjectId (FK canonical) ───────
    b_user = {"scanned": 0, "converted": 0, "skipped_invalid": 0}
    for doc in db.booking_orders.find(
        {"user_id": {"$type": "string"}}, {"_id": 1, "user_id": 1}
    ):
        b_user["scanned"] += 1
        raw = str(doc["user_id"]).strip()
        if len(raw) != 24 or not _is_hex24(raw):
            b_user["skipped_invalid"] += 1
            continue
        if apply:
            db.booking_orders.update_one(
                {"_id": doc["_id"]},
                {"$set": {"user_id": ObjectId(raw)}},
            )
        b_user["converted"] += 1
    result["booking_orders.user_id_str_to_objectid"] = b_user

    # ── 2. booking_orders.hotel_id backfill ────────────────────────────
    # ``{"hotel_id": None}`` matches both missing AND explicit-null fields
    # (MongoDB treats ``null`` queries as ``$exists``-agnostic).
    b_hotel = {"scanned": 0, "backfilled": 0, "unresolved": 0}
    for doc in db.booking_orders.find(
        {"hotel_id": None}, {"_id": 1, "prop_id": 1}
    ):
        b_hotel["scanned"] += 1
        hotel_oid = hotel_map.get(doc.get("prop_id"))
        if hotel_oid is None:
            b_hotel["unresolved"] += 1
            continue
        if apply:
            db.booking_orders.update_one(
                {"_id": doc["_id"]}, {"$set": {"hotel_id": hotel_oid}}
            )
        b_hotel["backfilled"] += 1
    result["booking_orders.hotel_id"] = b_hotel

    # ── 3. users.primary_role_id backfill ──────────────────────────────
    u_role = {"scanned": 0, "backfilled": 0, "unresolved": 0}
    for doc in db.users.find(
        {"primary_role_id": {"$exists": False}},
        {"_id": 1, "username": 1, "primary_role": 1},
    ):
        u_role["scanned"] += 1
        role_oid = role_map.get(doc.get("primary_role", ""))
        if role_oid is None:
            u_role["unresolved"] += 1
            continue
        if apply:
            db.users.update_one(
                {"_id": doc["_id"]},
                {"$set": {"primary_role_id": role_oid, "updated_at": _now()}},
            )
        u_role["backfilled"] += 1
    result["users.primary_role_id"] = u_role

    # ── 4. users.email_verified → true (missing rows) ──────────────────
    u_ev = {"scanned": 0, "backfilled": 0}
    for doc in db.users.find(
        {"email_verified": {"$exists": False}}, {"_id": 1, "username": 1}
    ):
        u_ev["scanned"] += 1
        if apply:
            db.users.update_one(
                {"_id": doc["_id"]},
                {"$set": {"email_verified": True, "updated_at": _now()}},
            )
        u_ev["backfilled"] += 1
    result["users.email_verified"] = u_ev

    # ── 5. hotel_products.hotel_id backfill ────────────────────────────
    p_hotel = {"scanned": 0, "backfilled": 0, "unresolved": 0}
    for doc in db.hotel_products.find(
        {"hotel_id": None}, {"_id": 1, "prop_id": 1, "product_id": 1}
    ):
        p_hotel["scanned"] += 1
        hotel_oid = hotel_map.get(doc.get("prop_id"))
        if hotel_oid is None:
            p_hotel["unresolved"] += 1
            continue
        if apply:
            db.hotel_products.update_one(
                {"_id": doc["_id"]}, {"$set": {"hotel_id": hotel_oid}}
            )
        p_hotel["backfilled"] += 1
    result["hotel_products.hotel_id"] = p_hotel

    # ── 6. room_types.hotel_id backfill ────────────────────────────────
    rt_hotel = {"scanned": 0, "backfilled": 0, "unresolved": 0}
    for doc in db.room_types.find(
        {"hotel_id": None}, {"_id": 1, "prop_id": 1, "room_type_id": 1}
    ):
        rt_hotel["scanned"] += 1
        hotel_oid = hotel_map.get(doc.get("prop_id"))
        if hotel_oid is None:
            rt_hotel["unresolved"] += 1
            continue
        if apply:
            db.room_types.update_one(
                {"_id": doc["_id"]}, {"$set": {"hotel_id": hotel_oid}}
            )
        rt_hotel["backfilled"] += 1
    result["room_types.hotel_id"] = rt_hotel

    # ── 7. room_inventory_calendar is_deleted/version backfill ─────────
    inv = {"scanned": 0, "backfilled": 0}
    for doc in db.room_inventory_calendar.find(
        {
            "$or": [
                {"is_deleted": {"$exists": False}},
                {"version": {"$exists": False}},
            ]
        },
        {"_id": 1},
    ):
        inv["scanned"] += 1
        update: dict[str, Any] = {}
        if "is_deleted" not in doc:
            update["is_deleted"] = False
        if "version" not in doc:
            update["version"] = 1
        if not update:
            continue
        if apply:
            db.room_inventory_calendar.update_one(
                {"_id": doc["_id"]}, {"$set": update}
            )
        inv["backfilled"] += 1
    result["room_inventory_calendar.is_deleted/version"] = inv

    # ── 8. permissions created_at/updated_at/is_system backfill ────────
    perm = {"scanned": 0, "backfilled": 0}
    for doc in db.permissions.find(
        {"created_at": {"$exists": False}}, {"_id": 1, "permission_code": 1}
    ):
        perm["scanned"] += 1
        if apply:
            now = _now()
            db.permissions.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "created_at": now,
                        "updated_at": now,
                        "is_system": True,
                    }
                },
            )
        perm["backfilled"] += 1
    result["permissions.audit_fields"] = perm

    # ── 9. employees.user_id: str → ObjectId (FK canonical) ──────────────
    emp_user = {"scanned": 0, "converted": 0, "skipped_invalid": 0}
    for doc in db.employees.find(
        {"user_id": {"$type": "string"}}, {"_id": 1, "user_id": 1}
    ):
        emp_user["scanned"] += 1
        raw = str(doc["user_id"]).strip()
        if len(raw) != 24 or not _is_hex24(raw):
            emp_user["skipped_invalid"] += 1
            continue
        if apply:
            db.employees.update_one(
                {"_id": doc["_id"]},
                {"$set": {"user_id": ObjectId(raw), "updated_at": _now()}},
            )
        emp_user["converted"] += 1
    result["employees.user_id_str_to_objectid"] = emp_user

    # ── 10. employee_shifts.employee_id: str → ObjectId (FK canonical) ──
    shift = {"scanned": 0, "converted": 0, "skipped_invalid": 0}
    for doc in db.employee_shifts.find(
        {"employee_id": {"$type": "string"}}, {"_id": 1, "employee_id": 1}
    ):
        shift["scanned"] += 1
        raw = str(doc["employee_id"]).strip()
        if len(raw) != 24 or not _is_hex24(raw):
            shift["skipped_invalid"] += 1
            continue
        if apply:
            db.employee_shifts.update_one(
                {"_id": doc["_id"]},
                {"$set": {"employee_id": ObjectId(raw), "updated_at": _now()}},
            )
        shift["converted"] += 1
    result["employee_shifts.employee_id_str_to_objectid"] = shift

    # ── 11. guest_folios.invoice_id: str → ObjectId (FK canonical) ──────
    # Same reference in reservation_payments.invoice_id is already ObjectId;
    # checkout/_checkout.py used to pass str(inv["_id"]) to close_folio.
    folio = {"scanned": 0, "converted": 0, "skipped_invalid": 0}
    for doc in db.guest_folios.find(
        {"invoice_id": {"$type": "string"}}, {"_id": 1, "invoice_id": 1}
    ):
        folio["scanned"] += 1
        raw = str(doc["invoice_id"]).strip()
        if len(raw) != 24 or not _is_hex24(raw):
            folio["skipped_invalid"] += 1
            continue
        if apply:
            db.guest_folios.update_one(
                {"_id": doc["_id"]},
                {"$set": {"invoice_id": ObjectId(raw), "updated_at": _now()}},
            )
        folio["converted"] += 1
    result["guest_folios.invoice_id_str_to_objectid"] = folio

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize operational schema drift (idempotent, deterministic backfills)"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Report changes without writing (default)")
    mode.add_argument("--apply", action="store_true", help="Persist deterministic backfills")
    args = parser.parse_args()
    result = migrate(apply=args.apply)
    import json

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
