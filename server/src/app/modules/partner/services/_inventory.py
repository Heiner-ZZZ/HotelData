"""Inventory layer drain helpers for FIFO/LIFO COGS accounting (Fase 6).

The ``fact_inventory`` collection tracks stock acquisitions as immutable
layers. Each layer has a single ``cost_per_unit`` (snapshot at acquisition
time) and ``qty_initial`` units. As products are sold (via
``booking_orders.line_items``), the COGS report drains layers in FIFO or
LIFO order, allocating per-unit cost from each layer until the sold
quantity is consumed.

Schema for ``fact_inventory`` doc::

    {
      "_id": ObjectId(...),
      "prop_id": int,
      "product_id": str,                    # e.g., "PROD-ABC123"
      "layer_id": str,                     # e.g., "INV-7f3e..." (semantic)
      "qty_initial": float,                # total units acquired
      "qty_remaining": float,              # decreases as drains happen
      "cost_per_unit": float,              # snapshot at acquisition time
      "acquired_at": datetime,             # sort key for FIFO/LIFO
      "source": str,                       # "restock" | "opening_stock" | "manual_adjustment"
      "supplier_name": str,                # optional snapshot from restock
      "invoice_ref": str,                  # optional snapshot from restock
      "consumed_at": datetime | None,      # set when qty_remaining hits 0
      "created_by": str,
      "is_active": bool = True,
    }

Edge cases handled:
  - Sold > sum of layers  → fallback to ``hotel_products.cost_price`` for
    the gap (recorded with ``source="fallback_layer_missing"``).
  - Sold before any layer exists → 100% fallback, same source tag.
  - Multiple layers same day → tie-break by ``_id`` ASC for deterministic
    FIFO ordering (oldest insertion first).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import secrets

from src.app.modules.partner.services._common import now_utc
from src.database.connection import get_database

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Insert path — used by restock_product().
# ---------------------------------------------------------------------------


def insert_inventory_layer(
    prop_id: int,
    product_id: str,
    *,
    qty: float,
    cost_per_unit: float,
    source: str = "restock",
    supplier_name: str = "",
    invoice_ref: str = "",
    inventory_event_id: str = "",
    acquired_at: datetime | None = None,
    created_by: str = "system",
) -> dict[str, Any]:
    """Insert one layer into ``fact_inventory``.

    Called from ``restock_product`` and from the backfill migration script.
    Returns the inserted doc (without ``_id`` projection).
    """
    db = get_database()
    doc = {
        "prop_id": int(prop_id),
        "product_id": product_id,
        "layer_id": f"INV-{secrets.token_hex(4).upper()}",
        "qty_initial": float(qty),
        "qty_remaining": float(qty),
        "cost_per_unit": round(float(cost_per_unit), 2),
        "acquired_at": acquired_at or now_utc(),
        "source": source,
        "supplier_name": supplier_name or "",
        "invoice_ref": invoice_ref or "",
        "inventory_event_id": inventory_event_id or invoice_ref or "",
        "consumed_at": None,
        "created_by": created_by,
        "is_active": True,
        "created_at": now_utc(),
    }
    db.fact_inventory.insert_one(doc)
    return doc


# ---------------------------------------------------------------------------
# Drain path — used by compute_cogs_report().
# ---------------------------------------------------------------------------


def _atomic_layer_decrement(
    db: Any,
    layer_id: Any,
    take: float,
) -> bool:
    """Atomically consume ``take`` units from one ``fact_inventory`` layer.

    Uses MongoDB's aggregation-pipeline update form (``update_one(..., [...])``,
    available since Mongo 4.2) for true single-roundtrip atomicity: the
    ``qty_remaining`` decrement, the ``is_active`` flip, and the
    ``consumed_at`` stamp all settle in one operation. The caller
    (``drain_layers_for_sale``) is therefore safe under concurrent
    callbacks — no read-then-write race where two drains can both believe
    they're taking 7 of 10.

    Guard: the update is gated by ``qty_remaining: {"$gte": take}``. If the
    layer no longer has enough units (e.g. another caller consumed them
    between our ``find()`` and this ``update_one()``), ``modified_count`` is
    0 and the caller re-fetches.

    Flips: when the **pre-decrement** ``qty_remaining <= take``, the layer
    reaches 0 (or below) and we set ``is_active=False`` + ``consumed_at:
    now``. Otherwise we preserve the prior ``is_active`` / ``consumed_at``.

    Returns
    -------
    bool
        ``True`` if exactly ``take`` units were atomically consumed.
        ``False`` if the ``$gte`` guard rejected the update (caller should
        re-fetch the layer).
    """
    if take <= 0:
        return True
    dec = round(float(take), 4)
    now = now_utc()
    result = db.fact_inventory.update_one(
        {
            "_id": layer_id,
            "qty_remaining": {"$gte": dec},
        },
        [
            {
                "$set": {
                    # ``$round`` keeps precision consistent with the
                    # historical ``round(..., 4)`` semantic that restocks
                    # and the migration script use.
                    "qty_remaining": {
                        "$round": [{"$subtract": ["$qty_remaining", dec]}, 4],
                    },
                    "consumed_at": {
                        "$cond": [
                            {
                                "$lte": [
                                    {"$subtract": ["$qty_remaining", dec]},
                                    0,
                                ],
                            },
                            now,
                            "$consumed_at",
                        ],
                    },
                    "is_active": {
                        "$cond": [
                            {
                                "$lte": [
                                    {"$subtract": ["$qty_remaining", dec]},
                                    0,
                                ],
                            },
                            False,
                            "$is_active",
                        ],
                    },
                }
            }
        ],
    )
    return result.modified_count >= 1


def drain_layers_for_sale(
    prop_id: int,
    product_id: str,
    units_to_drain: float,
    *,
    method: str = "fifo",
    persist: bool = True,
) -> dict[str, Any]:
    """Drain ``units_to_drain`` from product layers in FIFO or LIFO order.

    Args:
      prop_id, product_id: filter.
      units_to_drain: how many units were sold (consume this much).
      method: 'fifo' (oldest first) | 'lifo' (newest first) | 'approx'
              (pure fallback — skip layer drain, just multiply by
              ``hotel_products.cost_price``).
      persist: if True, write ``qty_remaining`` updates back to Mongo.
                Set False for read-only / preview paths.

    Returns:
      dict with:
        ``cogs``: float — total cost of goods sold for this product.
        ``layer_breakdown``: list[dict] — per-layer consumption:
            [{layer_id, units_consumed, cost_per_unit, source:
              "layer" | "fallback_layer_missing"}]
        ``fallback_units``: float — units that couldn't be matched to a
            layer (handled with ``hotel_products.cost_price``).
        ``avg_unit_cost``: float — weighted-average cost per unit
            (``cogs / units_to_drain`` if units_to_drain > 0 else 0).
    """
    db = get_database()
    units_to_drain = max(0.0, float(units_to_drain))

    fallback_cost = float(
        (db.hotel_products.find_one(
            {"prop_id": prop_id, "product_id": product_id},
            {"cost_price": 1, "_id": 0},
        ) or {}).get("cost_price", 0.0) or 0.0
    )

    if method == "approx":
        # Skip layer drain entirely; multiply directly. Mirrors Fase 5
        # behavior. Used for backward compat with existing reports.
        cogs = round(fallback_cost * units_to_drain, 2)
        return {
            "cogs": cogs,
            "layer_breakdown": [
                {
                    "layer_id": None,
                    "units_consumed": units_to_drain,
                    "cost_per_unit": fallback_cost,
                    "source": "approx_fallback",
                }
            ] if units_to_drain > 0 else [],
            "fallback_units": units_to_drain,
            "avg_unit_cost": fallback_cost,
        }

    # Fetch open layers for this product.
    cursor = db.fact_inventory.find(
        {
            "prop_id": prop_id,
            "product_id": product_id,
            "is_active": True,
            # Acquired by or before now (Fase 6 MVP ignores the temporal
            # alignment with the actual sale — drain latest open layers
            # chronologically. Future work: bound by line_items.added_at).
            "qty_remaining": {"$gt": 0},
        },
        {
            "_id": 1, "layer_id": 1, "qty_remaining": 1,
            "cost_per_unit": 1, "acquired_at": 1, "source": 1,
            "consumed_at": 1,
        },
    )
    if method == "fifo":
        layers = list(cursor.sort([("acquired_at", 1), ("_id", 1)]))
    elif method == "lifo":
        layers = list(cursor.sort([("acquired_at", -1), ("_id", -1)]))
    else:
        raise ValueError(f"Unknown method: {method!r}. Use fifo|lifo|approx.")

    breakdown: list[dict[str, Any]] = []
    remaining_units = units_to_drain
    total_cogs = 0.0

    # Phase 6 race-condition hardening (vs naive read-then-``$set``):
    #   Each layer-drain is an **atomic aggregation-pipeline update** with a
    #   ``qty_remaining: {``$gte``: take}`` guard. If a concurrent caller
    #   gets there first (``modified_count == 0``), we re-fetch that ONE
    #   layer and either retry with a smaller ``take`` or pop it. Adjusting
    #   only the contested layer preserves strict FIFO ordering — we never
    #   silently skip a partially-consumed older layer in favour of a newer
    #   one, because that would violate the cost-flow assumption.
    while layers and remaining_units > 0:
        layer = layers[0]
        local_avail = float(layer.get("qty_remaining", 0.0))
        if local_avail <= 0:
            layers.pop(0)
            continue

        take = min(local_avail, remaining_units)
        cost = round(float(layer.get("cost_per_unit", 0.0)) * take, 2)
        total_cogs += cost

        if persist:
            ok = _atomic_layer_decrement(
                db=db,
                layer_id=layer["_id"],
                take=take,
            )
            if not ok:
                # Concurrent drain raced us. Re-fetch THIS layer to know
                # whether to retry with smaller take (someone took 3 of 10
                # we wanted 7) or pop it (fully drained by another caller).
                fresh = db.fact_inventory.find_one(
                    {"_id": layer["_id"]},
                    {
                        "_id": 1, "layer_id": 1, "qty_remaining": 1,
                        "cost_per_unit": 1, "acquired_at": 1, "source": 1,
                    },
                )
                if fresh and float(fresh.get("qty_remaining", 0.0)) > 0:
                    layers[0] = fresh  # retry same layer with new avail
                else:
                    layers.pop(0)  # fully drained externally
                continue  # loop top; do NOT record this attempt in breakdown

        # Record breakdown AFTER the atomic decrement succeeded (or in the
        # persist=False preview path).
        breakdown.append({
            "layer_id": layer.get("layer_id"),
            "units_consumed": take,
            "cost_per_unit": float(layer.get("cost_per_unit", 0.0)),
            "source": "layer",
        })
        local_avail = round(local_avail - take, 4)
        if local_avail <= 0:
            layers.pop(0)
        else:
            layer["qty_remaining"] = local_avail
        remaining_units -= take

    fallback_units = max(0.0, remaining_units)
    if fallback_units > 0:
        fallback_cogs = round(fallback_cost * fallback_units, 2)
        total_cogs += fallback_cogs
        breakdown.append({
            "layer_id": None,
            "units_consumed": fallback_units,
            "cost_per_unit": fallback_cost,
            "source": "fallback_layer_missing",
        })

    avg_unit_cost = round(total_cogs / units_to_drain, 4) if units_to_drain > 0 else 0.0
    return {
        "cogs": round(total_cogs, 2),
        "layer_breakdown": breakdown,
        "fallback_units": fallback_units,
        "avg_unit_cost": avg_unit_cost,
    }
