#!/usr/bin/env python3
"""Cleanup: remove smoke/test seed data and revert the product state it changed.

Purpose
-------
During feature work we insert ``Smoke*`` test records directly into the dev
database (restock smoke tests, throwaway expense invoices, and their ledger +
audit trail). This script sweeps ALL of them so the dev DB can go back to a
clean, demo-only state, and so the cleanup is repeatable after future smokes.

What it removes (idempotent, safe to re-run):
  1. Expense invoices whose ``vendor_name`` matches ``/smoke/i``, PLUS any
     orphan invoice whose ``prop_id`` is null/absent (a real invoice always
     belongs to a property — a null prop_id means test data like
     ``Products Listii`` that the ``/smoke/i`` filter never catches).
  2. ``fact_inventory`` layers linked to a smoke restock:
       - via the smoke restock audit's ``metadata.fact_inventory_layer_id``, or
       - via ``invoice_ref`` pointing at a removed smoke invoice, or
       - standalone layers whose ``supplier_name`` matches ``/smoke/i``.
  3. ``ledger_transactions`` rows of the smoke journals:
       - via the smoke restock audit's ``metadata.journal_entry_id``, or
       - best-effort: rows whose description/reference mentions smoke.
  4. The smoke restock ``audit_log`` rows themselves (entity_type
     ``hotel_product_stock`` whose summary/diff/metadata mentions smoke).
  5. Smoke/throwaway bookings (full footprint across every collection that
     carries ``booking_id``): identifiers like ``BK-SMOKE01`` (the smoke test
     restock booking) and manual-reservation tests under the guest
     ``Test Manual User``. The booking itself, its status history, guests,
     manual-reservation record, notifications, folio and payments are all
     removed together so no orphaned rows survive.

What it restores (undoing what the restock did)
-----------------------------------------------
For every smoke restock audit found, the ``diff`` records the pre-smoke
(``old``) value of ``quantity_available``, ``cost_price``,
``default_supplier`` and ``last_purchase_invoice_ref``. The script restores
those fields on the product, and clears the last-purchase trail
(``last_purchase_at`` / ``last_purchase_qty``) when the product's current ref
points at a smoke invoice that is being removed.

Why the audit is the source of truth: the restock code path (``restock_product``
in ``partner/services/hotel_products.py``) writes an audit row whose
``metadata`` carries ``journal_entry_id`` / ``fact_inventory_layer_id`` and whose
``diff`` carries the exact pre-smoke values. Deleting the layer without restoring
the product would leave stock/cost silently inflated.

Idempotency
-----------
- Deletes are naturally idempotent (``delete_many`` with the same filter returns
  0 on the second run).
- Audit-driven restores run only for audits that still exist; once an audit row
  is consumed (removed) it will not be re-processed, so product fields are never
  double-restored.
- No ``delete_many`` + ``insert`` rewrites; only targeted deletes + ``$set``.

Scope guard
-----------
- Applies to whatever database ``get_database()`` resolves to (dev
  ``hoteldata_hub`` in the standard compose setup). Use ``--prop-id`` to
  restrict product restores to one property.
- Deliberately does NOT touch: seeded demo data ("Proveedor Demo",
  ``cliente1@test.com``) or the ``RT-99999-test`` room type (that room type
  needs a human decision, not a blanket sweep).
- Smoke bookings ARE swept, but only by explicit, conservative patterns:
  ``booking_id`` starting with ``BK-SMOKE``, or the guest name
  ``Test Manual User``. Any real reservation that ever matches one of those
  patterns would be swept too, but the identifiers are chosen to be
  unmistakably test-only.

Run
---
    python /app/scripts/cleanup_smoke_test_data.py [--dry-run] [--prop-id N]
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database

SMOKE_RE = re.compile(r"smoke", re.IGNORECASE)

COLL_INVOICES = "expense_invoices"
COLL_LAYERS = "fact_inventory"
COLL_LEDGER = "ledger_transactions"
COLL_AUDIT = "audit_log"
COLL_PRODUCTS = "hotel_products"
COLL_BOOKINGS = "booking_orders"

# Bookings smoke sweep: identifiers that are unmistakably test-only.
SMOKE_BOOKING_ID_RE = re.compile(r"^BK-SMOKE", re.IGNORECASE)
MANUAL_TEST_GUEST_RE = re.compile(r"test manual user", re.IGNORECASE)

# Every collection verified to store a ``booking_id`` field (checked against
# the live dev DB) — the smoke-booking sweep deletes from all of them so no
# orphaned rows survive. NOTE: ``housekeeping_tasks`` does NOT carry
# ``booking_id`` (verified) and ``audit_log`` references bookings via
# ``entity_id`` (handled separately), so neither belongs here.
BOOKING_BEARING_COLLECTIONS = [
    "booking_orders",
    "booking_status_history",
    "booking_guests",
    "manual_reservations",
    "notification_log",
    "guest_folios",
    "reservation_payments",
    "stay_sessions",
    "stay_service_requests",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _s(text: Any) -> str:
    return "" if text is None else str(text)


def _doc_blob(*values: Any) -> str:
    """Join several doc fields into one searchable lowercase string."""
    return " ".join(_s(v) for v in values).lower()


# ─── Discovery ────────────────────────────────────────────────────────────


def find_smoke_invoices(db: Any) -> list[dict[str, Any]]:
    """Expense invoices whose vendor name mentions smoke."""
    return list(db[COLL_INVOICES].find({"vendor_name": SMOKE_RE}))


def find_orphan_invoices(db: Any) -> list[dict[str, Any]]:
    """Invoices with no property (``prop_id`` null/absent).

    A real invoice always belongs to a property; a null ``prop_id`` marks
    throwaway test data (e.g. ``Products Listii``) that the ``/smoke/i``
    vendor filter never catches. Both ``None`` and missing match the same
    query because MongoDB treats ``{"prop_id": None}`` as "is null".
    """
    return list(db[COLL_INVOICES].find({"prop_id": None}))


def find_smoke_bookings(db: Any) -> list[dict[str, Any]]:
    """Smoke/throwaway bookings by conservative identifier patterns.

    Matches ``BK-SMOKE*`` booking ids (the smoke restock booking) or the
    guest ``Test Manual User`` (manual-reservation API test). Returns the
    unique booking ids; the per-collection footprint is resolved in
    ``_booking_footprint``.
    """
    ids: list[str] = []
    for doc in db[COLL_BOOKINGS].find(
        {"$or": [{"booking_id": SMOKE_BOOKING_ID_RE}, {"guest_name": MANUAL_TEST_GUEST_RE}]},
        {"booking_id": 1},
    ):
        bid = doc.get("booking_id")
        if bid and bid not in ids:
            ids.append(bid)
    return ids


def _booking_footprint(db: Any, booking_id: str) -> dict[str, int]:
    """Count rows referencing ``booking_id`` across every booking-bearing collection."""
    counts: dict[str, int] = {}
    for coll in BOOKING_BEARING_COLLECTIONS:
        n = db[coll].count_documents({"booking_id": booking_id})
        if n:
            counts[coll] = n
    return counts


def find_smoke_restock_audits(db: Any) -> list[dict[str, Any]]:
    """Restock audit rows whose summary/diff/metadata mention smoke.

    These are the source of truth for the layer/journal ids to remove and the
    pre-smoke product values to restore.
    """
    rows = db[COLL_AUDIT].find(
        {"entity_type": "hotel_product_stock", "action": "restock"}
    )
    return [
        row for row in rows
        if SMOKE_RE.search(_doc_blob(row.get("summary"), row.get("diff"), row.get("metadata")))
    ]


def find_smoke_layers(db: Any, smoke_invoice_ids: set[str]) -> list[dict[str, Any]]:
    """Layers linked to smoke: by audit metadata, by invoice_ref, or by supplier."""
    query: dict[str, Any] = {"$or": [{"supplier_name": SMOKE_RE}]}
    if smoke_invoice_ids:
        query["$or"].append({"invoice_ref": {"$in": sorted(smoke_invoice_ids)}})
    return list(db[COLL_LAYERS].find(query))


def find_smoke_ledger(db: Any, smoke_journal_ids: set[str]) -> list[dict[str, Any]]:
    """Ledger rows of smoke journals; best-effort by description/reference too."""
    or_clauses: list[dict[str, Any]] = [
        {"description": SMOKE_RE},
        {"reference": SMOKE_RE},
    ]
    if smoke_journal_ids:
        or_clauses.insert(0, {"journal_entry_id": {"$in": sorted(smoke_journal_ids)}})
    return list(db[COLL_LEDGER].find({"$or": or_clauses}))


# ─── Apply helpers ────────────────────────────────────────────────────────


def _product_id_from_audit(audit: dict[str, Any]) -> str:
    """entity_id is stored as ``in:PROD-XXXX`` for restock audits."""
    eid = _s(audit.get("entity_id"))
    return eid.removeprefix("in:") if eid else ""


def _build_product_restores(
    db: Any,
    audits: list[dict[str, Any]],
    *,
    smoke_invoice_ids: set[str],
    prop_id: int | None,
) -> list[dict[str, Any]]:
    """Revert product fields changed by smoke restocks, grouped per product.

    Smoke restocks can be STACKED on the same product (e.g. "Smoke Test Co"
    followed by "Smoke2" minutes later). Each audit's ``diff.old`` is the state
    just before THAT restock, so the newest audit's ``old`` is polluted by the
    earlier smoke. The correct source of truth is:

      - quantity_available: current - SUM(qty_added of ALL smoke audits)
      - cost_price / default_supplier / last_purchase_invoice_ref:
        the ``old`` values of the OLDEST smoke audit (true pre-smoke state)

    ``metadata.qty_added`` may be missing on legacy smoke audits; in that case
    the per-audit ``diff.quantity_available.old/new`` delta is used instead.
    """
    by_product: dict[str, list[dict[str, Any]]] = {}
    for audit in audits:
        pid = _product_id_from_audit(audit)
        if pid:
            by_product.setdefault(pid, []).append(audit)

    restores: list[dict[str, Any]] = []
    for product_id, group in by_product.items():
        # Oldest first so the first audit's diff holds the true pre-smoke state.
        group.sort(key=lambda a: _s(a.get("timestamp") or a.get("created_at")))
        query: dict[str, Any] = {"product_id": product_id}
        if prop_id is not None:
            query["prop_id"] = prop_id
        product = db[COLL_PRODUCTS].find_one(query)
        if product is None:
            continue

        diffs = [(a.get("diff") or {}) for a in group]
        updates: dict[str, Any] = {}
        unsets: dict[str, str] = {}

        # Quantity: subtract the total added by ALL smoke restocks of this product.
        total_added = 0.0
        for a in group:
            meta = a.get("metadata") or {}
            qty = float(meta.get("qty_added", 0) or 0)
            if not qty:
                dq = (a.get("diff") or {}).get("quantity_available")
                if isinstance(dq, dict):
                    try:
                        qty = float(dq.get("new") or 0) - float(dq.get("old") or 0)
                    except (TypeError, ValueError):
                        qty = 0.0
            total_added += qty
        if total_added:
            current_qty = float(product.get("quantity_available", 0) or 0)
            updates["quantity_available"] = round(max(0.0, current_qty - total_added), 2)

        # Scalar fields: prefer the OLDEST smoke diff that records each field.
        # ``group`` is sorted oldest-first, so the first diff holding an ``old``
        # value for a field is the true pre-smoke state for that field (a later
        # stacked smoke's ``old`` would be polluted by the earlier smoke).
        for field in ("cost_price", "default_supplier", "last_purchase_invoice_ref"):
            for diff in diffs:
                entry = diff.get(field)
                if isinstance(entry, dict) and "old" in entry:
                    updates[field] = entry["old"]
                    break

        # Last-purchase trail: if the current ref was written by a smoke (points
        # at a removed smoke invoice or matches a smoke diff.new), restore it and
        # drop at/qty (the smoke overwrote them; the diff does not record old).
        current_ref = _s(product.get("last_purchase_invoice_ref"))
        smoke_refs = set(smoke_invoice_ids)
        for a in group:
            dref = (a.get("diff") or {}).get("last_purchase_invoice_ref")
            if isinstance(dref, dict):
                smoke_refs.add(_s(dref.get("new")))
        # Also treat a missing/empty ref as smoke-written when any audit recorded
        # a non-empty smoke ``new`` ref, so stale at/qty can't survive a ref clear.
        smoke_refs.discard("")
        ref_was_smoke = current_ref in smoke_refs or (
            not current_ref and bool(smoke_refs)
        )
        if ref_was_smoke:
            updates["last_purchase_invoice_ref"] = None
            for diff in diffs:
                entry = diff.get("last_purchase_invoice_ref")
                if isinstance(entry, dict) and "old" in entry:
                    updates["last_purchase_invoice_ref"] = entry["old"]
                    break
            unsets["last_purchase_at"] = ""
            unsets["last_purchase_qty"] = ""

        updates["updated_at"] = utc_now()
        updates["updated_by"] = "cleanup_smoke_test_data"

        restores.append(
            {
                "product_id": product_id,
                "prop_id": product.get("prop_id"),
                "name": product.get("name"),
                "updates": updates,
                "unsets": list(unsets),
            }
        )
    return restores


# ─── Report ───────────────────────────────────────────────────────────────


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Remove smoke/test seed data and revert the products it changed."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be removed/restored without changing anything.",
    )
    parser.add_argument(
        "--prop-id",
        type=int,
        default=None,
        help="Restrict product restores to a single prop_id.",
    )
    args = parser.parse_args(argv)

    db = get_database()

    invoices = find_smoke_invoices(db)
    orphan_invoices = find_orphan_invoices(db)
    audits = find_smoke_restock_audits(db)
    smoke_booking_ids = find_smoke_bookings(db)

    # Orphan invoices must not double-count when they also match /smoke/i.
    smoke_invoice_ids_all = {i["_id"] for i in invoices}
    orphan_only = [inv for inv in orphan_invoices if inv.get("_id") not in smoke_invoice_ids_all]
    all_invoices = invoices + orphan_only

    smoke_invoice_ids = {_s(inv.get("_id")) for inv in all_invoices}
    smoke_journal_ids = {
        _s(a.get("metadata", {}).get("journal_entry_id")) if isinstance(a.get("metadata"), dict) else ""
        for a in audits
    }
    smoke_journal_ids.discard("")

    layers = find_smoke_layers(db, smoke_invoice_ids)
    ledger = find_smoke_ledger(db, smoke_journal_ids)
    restores = _build_product_restores(
        db, audits, smoke_invoice_ids=smoke_invoice_ids, prop_id=args.prop_id
    )

    # Booking smoke footprint: total rows that WILL be removed per booking.
    booking_footprints = {bid: _booking_footprint(db, bid) for bid in smoke_booking_ids}
    # ``audit_log`` references bookings via ``entity_id`` (no booking_id field).
    # Count those rows too so the dry-run report shows the full blast radius.
    booking_audit_counts = {
        bid: db[COLL_AUDIT].count_documents({"entity_id": bid})
        for bid in smoke_booking_ids
    }

    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"[{mode}] database={db.name} prop_id={args.prop_id or 'ALL'}")
    print(f"  expense_invoices  : {len(invoices)} smoke + {len(orphan_only)} orphan (prop_id null)")
    print(f"  restock audits    : {len(audits)} smoke (source of truth)")
    print(f"  fact_inventory    : {len(layers)} smoke layers")
    print(f"  ledger_transactions: {len(ledger)} smoke rows")
    print(f"  product restores  : {len(restores)}")
    print(f"  smoke bookings    : {len(smoke_booking_ids)}")

    for inv in all_invoices:
        print(f"    - invoice {_s(inv.get('_id'))} vendor={inv.get('vendor_name')} prop={inv.get('prop_id')}")
    for layer in layers:
        print(f"    - layer {layer.get('layer_id')} product={layer.get('product_id')} supplier={layer.get('supplier_name')} ref={_s(layer.get('invoice_ref'))[:24]}")
    for row in ledger:
        print(f"    - ledger {row.get('journal_entry_id')} {row.get('account_code')} {_s(row.get('description'))[:60]}")
    for r in restores:
        print(
            f"    - restore {r['product_id']} (prop {r['prop_id']}): "
            f"{r['updates']} unset={r['unsets']}"
        )
    for bid, counts in booking_footprints.items():
        detail = ", ".join(f"{c}={n}" for c, n in counts.items()) or "(no rows)"
        audit_n = booking_audit_counts.get(bid, 0)
        if audit_n:
            detail += f", audit_log(entity_id)={audit_n}"
        print(f"    - booking {bid} -> {detail}")

    if args.dry_run:
        print("No changes applied (--dry-run).")
        return 0

    for inv in all_invoices:
        db[COLL_INVOICES].delete_one({"_id": inv["_id"]})
    for layer in layers:
        db[COLL_LAYERS].delete_many({"_id": layer["_id"]})
    for row in ledger:
        db[COLL_LEDGER].delete_many({"_id": row["_id"]})

    # Product restores are applied BEFORE their audit rows are removed, so a
    # crash mid-run cannot double-restore on the next invocation.
    for r in restores:
        updates = dict(r["updates"])
        unsets = {key: "" for key in r["unsets"]}
        # Project convention (repair_zero_invoices / migrate_* scripts): stamp the
        # change with a script marker so it is auditable after the fact.
        updates["metadata.cleanup_smoke_test_data"] = {"at": utc_now()}
        db[COLL_PRODUCTS].update_one(
            {"product_id": r["product_id"]},
            {"$set": updates, "$unset": unsets},
        )

    # Remove the consumed smoke restock audits last (idempotency marker).
    audit_ids = [a["_id"] for a in audits]
    if audit_ids:
        db[COLL_AUDIT].delete_many({"_id": {"$in": audit_ids}})

    # Smoke booking footprint: sweep every booking-bearing collection for the
    # identified booking ids so no orphaned rows survive.
    for bid in smoke_booking_ids:
        for coll in BOOKING_BEARING_COLLECTIONS:
            db[coll].delete_many({"booking_id": bid})
        # audit_log rows that reference the booking via entity_id. Only match
        # the conservative smoke patterns here (never a plain string match on
        # entity_id, which could collide with other entity types).
        db[COLL_AUDIT].delete_many({"entity_id": bid})

    print(
        f"Done: removed {len(all_invoices)} invoice(s), {len(layers)} layer(s), "
        f"{len(ledger)} ledger row(s), {len(audits)} audit row(s), "
        f"{len(smoke_booking_ids)} booking(s); restored {len(restores)} product(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
