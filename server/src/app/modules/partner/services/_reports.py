"""Aggregation helpers for the 3 product reports (margin / COGS / stock-value).

Computed in pure Python over MongoDB rows (not pipelines) so the numbers can
be reasoned about without clicking through Stadium. Pragmatic for <10K
products / month; revisit with aggregation pipelines if performance bites.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from dateutil.relativedelta import relativedelta

from src.app.modules.partner.services._common import now_utc
from src.app.modules.partner.services._inventory import drain_layers_for_sale
from src.database.connection import get_database


def compute_margin_report(prop_id: int) -> dict[str, Any]:
    """Aggregate margin (% + absolute) per product + summary.

    Filter:
      - ``is_active=True`` only.
      - ``archived_at=None``.

    Math:
      - ``margin_abs = unit_price - cost_price``
      - ``margin_pct = (margin_abs / unit_price) * 100``  (0 if unit_price <= 0)
    """
    db = get_database()
    products = list(
        db.hotel_products.find(
            {"prop_id": prop_id, "is_active": True, "archived_at": None},
        )
    )

    items = []
    total_margin_abs = 0.0
    total_unit_price = 0.0

    for p in products:
        cost = float(p.get("cost_price", 0.0) or 0.0)
        price = float(p.get("unit_price", 0.0) or 0.0)
        margin_abs = round(price - cost, 2)
        margin_pct = round((margin_abs / price) * 100, 2) if price > 0 else 0.0

        total_margin_abs += margin_abs
        total_unit_price += price

        items.append({
            "_id": p["_id"],
            "product_id": p.get("product_id", ""),
            "name": p.get("name", ""),
            "category": p.get("category", "Otros"),
            "type": p.get("type", "retail"),
            "cost_price": cost,
            "unit_price": price,
            "margin_abs": margin_abs,
            "margin_pct": margin_pct,
            "quantity_available": int(p.get("quantity_available", 0) or 0),
        })

    items.sort(key=lambda x: x["margin_pct"], reverse=True)
    global_pct = round((total_margin_abs / total_unit_price) * 100, 2) if total_unit_price > 0 else 0.0

    # ``active_products`` was dropped because it was always equal to
    # ``total_products`` (the filter already excludes archived + inactive).
    # If we ever need a separate counter (e.g. ``inactive_count``), compute
    # it against the unfiltered query before this branch.
    return {
        "summary": {
            "total_products": len(items),
            "total_margin_abs": round(total_margin_abs, 2),
            "total_unit_price": round(total_unit_price, 2),
            "global_margin_pct": global_pct,
        },
        "items": items,
    }


def compute_stock_value_report(prop_id: int) -> dict[str, Any]:
    """Aggregate stock value (qty × cost_price) per product + by-category summary.

    Filter:
      - ``is_active=True`` only.
      - ``archived_at=None`` (consistent with ``compute_margin_report`` so
        phantom residual stock doesn't appear in the valuation).
      - Includes qty=0 products for visibility (stock_value = 0).
    """
    db = get_database()
    products = list(
        db.hotel_products.find(
            {"prop_id": prop_id, "is_active": True, "archived_at": None},
        )
    )

    items = []
    cat_map: dict[str, dict[str, Any]] = {}
    total_value = 0.0
    total_units = 0

    for p in products:
        cost = float(p.get("cost_price", 0.0) or 0.0)
        qty = max(0, int(p.get("quantity_available", 0) or 0))
        value = round(cost * qty, 2)
        category = p.get("category", "Otros")

        total_value += value
        total_units += qty

        if category not in cat_map:
            cat_map[category] = {
                "category": category,
                "total_value": 0.0,
                "units": 0,
                "products": 0,
            }
        cat_map[category]["total_value"] = round(cat_map[category]["total_value"] + value, 2)
        cat_map[category]["units"] += qty
        cat_map[category]["products"] += 1

        items.append({
            "_id": p["_id"],
            "product_id": p.get("product_id", ""),
            "name": p.get("name", ""),
            "category": category,
            "quantity_available": qty,
            "cost_price": cost,
            "stock_value": value,
        })

    by_category = sorted(cat_map.values(), key=lambda x: x["total_value"], reverse=True)
    items.sort(key=lambda x: x["stock_value"], reverse=True)

    return {
        "as_of": now_utc().isoformat(),
        "summary": {
            "total_stock_value": round(total_value, 2),
            "total_units": total_units,
            "distinct_products": len(items),
        },
        "by_category": by_category,
        "items": items,
    }


def compute_cogs_report(
    prop_id: int,
    period: str,
    method: str = "fifo",
) -> dict[str, Any]:
    """Compute Cost of Goods Sold over a period using FIFO/LIFO/approx layer drain.

    Fase 6 — replaces the Fase 5 last-purchase approximation with real layer
    accounting via ``drain_layers_for_sale()``. Each unit sold drains from
    ``fact_inventory`` layers in the requested order:

      ``fifo``   — oldest layer first (default, GAAP-aligned).
      ``lifo``   — newest layer first (tax-advantaged in some jurisdictions).
      ``approx`` — skip layer drain; multiply by current ``hotel_products.cost_price``
                   (mirrors Fase 5 behavior; useful when a hotel has not yet
                   run the migration script).

    ``persist=True`` for fifo/lifo writes back ``qty_remaining`` to Mongo so
    successive reports show layered consumption over time.

    Period semantics:
      - ``month``  → first day of current month → now
      - ``week``   → Monday of current week → now
      - ``year``   → Jan 1 of current year → now
      - ``all``    → 5 years back → now

    Note on temporal alignment (intentional v1 simplification): layers are
    drained in chronological order of ``acquired_at`` regardless of when the
    actual sale (``line_items.added_at``) happened. Full sale-bounded drift
    would require time-window approximation in ``drain_layers_for_sale``
    (e.g. cap layers by ``acquired_at <= sale_at``). Out of scope for MVP.
    """
    db = get_database()

    now = now_utc()
    if period == "month":
        start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        days_into_week = now.weekday()
        start_dt = (now - timedelta(days=days_into_week)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start_dt = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # all
        start_dt = now - relativedelta(years=5)

    pipeline = [
        {"$match": {"prop_id": prop_id, "line_items.added_at": {"$gte": start_dt}}},
        {"$unwind": "$line_items"},
        {"$match": {"line_items.added_at": {"$gte": start_dt}}},
        {
            "$group": {
                "_id": "$line_items.product_id",
                "name": {"$last": "$line_items.name"},
                "units_sold": {"$sum": "$line_items.quantity"},
            }
        },
    ]
    sold_rows = list(db.booking_orders.aggregate(pipeline))

    product_ids = [r["_id"] for r in sold_rows if r.get("_id")]
    catalog = {
        p["product_id"]: p
        for p in db.hotel_products.find(
            {"prop_id": prop_id, "product_id": {"$in": product_ids}}
        )
    }

    items = []
    total_cogs = 0.0
    total_units_sold = 0
    total_fallback_units = 0

    for row in sold_rows:
        pid = row.get("_id")
        if not pid:
            continue
        meta = catalog.get(pid, {})
        units = int(row.get("units_sold", 0) or 0)
        if units <= 0:
            continue

        # Drain layers FIFO/LIFO/approx. For fifo/lifo, persist updates
        # ``qty_remaining`` on ``fact_inventory`` so successive reports show
        # layered consumption over time.
        drain = drain_layers_for_sale(
            prop_id=prop_id,
            product_id=pid,
            units_to_drain=units,
            method=method,
            persist=True,
        )

        cogs = drain["cogs"]
        total_cogs += cogs
        total_units_sold += units
        total_fallback_units += int(drain.get("fallback_units", 0))

        items.append({
            "product_id": pid,
            "name": row.get("name", ""),
            "category": meta.get("category", "Otros"),
            "units_sold": units,
            # When ``method in (fifo, lifo)`` this is the weighted-average cost
            # across the layers drained. When ``method == approx`` it equals
            # the current ``hotel_products.cost_price`` snapshot.
            "avg_unit_cost": drain.get("avg_unit_cost", 0.0),
            "cogs": cogs,
            # Per-layer consumption breakdown (one entry per layer touched
            # + an optional fallback row when sold > available layers).
            # Enables UI drill-down: "COGS this month came from 30 units @
            # $2.40 + 10 units @ $2.80 (FIFO)".
            "layer_breakdown": drain.get("layer_breakdown", []),
        })

    items.sort(key=lambda x: x["cogs"], reverse=True)

    return {
        # Echo the requested method so the UI can label itself; useful when
        # the same report is fetched with different method params in quick
        # succession (caching layer will collapse, and the label here is the
        # canonical truth for that snapshot).
        "method": method,
        "period": period,
        "period_start": start_dt.isoformat(),
        "period_end": now.isoformat(),
        "summary": {
            "total_cogs": round(total_cogs, 2),
            "units_sold": total_units_sold,
            "distinct_products_sold": len(items),
            # ``fallback_units_across_products`` is the SUM (across items)
            # of units that could not be matched to a layer. Non-zero when:
            #  - the migration ``migrate_inventory_layers`` hasn't run yet, OR
            #  - a product's layers are exhausted mid-period (over-sold vs
            #    available acquisition hx).
            "fallback_units_across_products": total_fallback_units,
        },
        "items": items,
    }
