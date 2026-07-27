"""Tests for compute_cogs_report (Fase 6: layer-aware COGS with FIFO/LIFO/approx).

Covers:
- Empty state: no booking_orders yields items=[]
- Period filtering: ``month``/``week`` excludes older ``line_items.added_at``
- ``method`` switch: fifo drains oldest layers, lifo drains newest layers,
  approx multiplies by ``cost_price`` snapshot, ``unknown`` raises
- Fallback aggregation: ``summary.fallback_units_across_products`` sums
  across products
- Persistence invariant: successive reports show layered consumption
  when fifo/lifo persist=True
- Line items without a ``product_id`` are silently ignored
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.app.modules.partner.services._reports import (
    compute_cogs_report,
)
from src.app.modules.partner.services._inventory import (
    insert_inventory_layer,
)


# ───────────────────────────── Helpers ─────────────────────────────


def _seed_product(db, *, prop_id: int = 1, product_id: str = "PROD-COGS01",
                  cost_price: float = 2.00, unit_price: float = 5.0,
                  category: str = "Bebidas") -> str:
    db.hotel_products.insert_one({
        "prop_id": prop_id,
        "product_id": product_id,
        "name": "Water Bottle",
        "unit_price": float(unit_price),
        "cost_price": float(cost_price),
        "quantity_available": 100,
        "category": category,
        "is_active": True,
        "created_by": "test_seed",
    })
    return product_id


def _seed_booking_with_lines(
    db, *, prop_id: int = 1, booking_id: str = "BK-COGS01",
    product_id: str = "PROD-COGS01", units: int = 5,
    added_at: datetime | None = None,
    name: str = "Water Bottle",
) -> str:
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": prop_id,
        "status": "confirmed",
        "line_items": [{
            "item_id": "LI-1",
            "product_id": product_id,
            "name": name,
            "quantity": int(units),
            "unit_price": 5.0,
            "total": float(units * 5.0),
            "added_at": added_at or datetime.now(timezone.utc),
            "added_by": "system",
        }],
        "total_charges": float(units * 5.0),
    })
    return booking_id


# ─────────────────────────── Fixtures ────────────────────────────


@pytest.fixture
def month_start_anchor():
    """Anchor for tests verifying ``line_items.added_at`` window semantics."""
    return datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    )


# ─────────────────────────── Tests ────────────────────────────


class TestComputeCogsEmpty:
    def test_no_booking_orders_returns_empty_items(self, db, seeded_product_with_cost=None):
        """No line items in the period → empty items, distinct=0."""
        _seed_product(db, product_id="PROD-SOMETHING")
        result = compute_cogs_report(prop_id=1, period="month", method="fifo")
        assert result["method"] == "fifo"
        assert result["period"] == "month"
        assert result["items"] == []
        assert result["summary"]["total_cogs"] == 0.0
        assert result["summary"]["units_sold"] == 0
        assert result["summary"]["distinct_products_sold"] == 0
        assert result["summary"]["fallback_units_across_products"] == 0


class TestComputeCogsPeriods:
    def test_month_period_includes_recent_sales(
        self, db, month_start_anchor,
    ):
        _seed_product(db, product_id="PROD-COGS01")
        _seed_booking_with_lines(
            db, units=5, added_at=month_start_anchor + timedelta(days=2),
        )
        result = compute_cogs_report(prop_id=1, period="month", method="approx")
        assert result["summary"]["units_sold"] == 5
        assert len(result["items"]) == 1
        assert result["items"][0]["product_id"] == "PROD-COGS01"

    def test_month_period_excludes_older_sales(
        self, db, month_start_anchor,
    ):
        """Sales BEFORE the current month start must be excluded from ``month``."""
        _seed_product(db, product_id="PROD-COGS01")
        _seed_booking_with_lines(
            db, booking_id="BK-OLD",
            units=20,
            added_at=month_start_anchor - timedelta(days=1),
        )
        result = compute_cogs_report(prop_id=1, period="month", method="approx")
        assert result["summary"]["units_sold"] == 0
        assert result["items"] == []

    def test_all_period_includes_old_sales(
        self, db, month_start_anchor,
    ):
        """``all`` selects a 5-year window, so it should pick up old sales."""
        _seed_product(db, product_id="PROD-COGS01")
        _seed_booking_with_lines(
            db, booking_id="BK-OLD",
            units=15,
            added_at=month_start_anchor - timedelta(days=400),
        )
        result = compute_cogs_report(prop_id=1, period="all", method="approx")
        assert result["summary"]["units_sold"] == 15


@pytest.fixture
def two_fifo_layers(db):
    """Insert 2 layers: 10 @ $1.00 (old), 20 @ $3.00 (newer)."""
    _seed_product(db, product_id="PROD-COGS01", cost_price=2.00)
    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    insert_inventory_layer(
        prop_id=1, product_id="PROD-COGS01",
        qty=10.0, cost_per_unit=1.00,
        acquired_at=base, source="opening_stock",
    )
    insert_inventory_layer(
        prop_id=1, product_id="PROD-COGS01",
        qty=20.0, cost_per_unit=3.00,
        acquired_at=base + timedelta(days=2), source="opening_stock",
    )
    return {"base": base}


class TestComputeCogsMethods:
    def test_fifo_method_drains_layers_chronologically(self, db, two_fifo_layers):
        _seed_booking_with_lines(db, units=15, product_id="PROD-COGS01")
        result = compute_cogs_report(prop_id=1, period="month", method="fifo")
        # FIFO: 10 @ 1.00 + 5 @ 3.00 = 25.00
        assert result["method"] == "fifo"
        row = result["items"][0]
        assert row["cogs"] == 25.00
        assert row["units_sold"] == 15
        assert row["avg_unit_cost"] == pytest.approx(25.0 / 15.0, abs=1e-4)
        # Per-layer breakdown with two layer entries (no fallback).
        breakdown = row["layer_breakdown"]
        assert len(breakdown) == 2
        assert breakdown[0]["source"] == "layer"
        assert breakdown[0]["units_consumed"] == 10.0
        assert breakdown[0]["cost_per_unit"] == 1.00
        assert breakdown[1]["source"] == "layer"
        assert breakdown[1]["units_consumed"] == 5.0
        assert breakdown[1]["cost_per_unit"] == 3.00

    def test_lifo_method_drains_newest_first(self, db, two_fifo_layers):
        """LIFO: 15 of the 20-latest @ 3.00 = 45.00 (no fallback)."""
        _seed_booking_with_lines(db, units=15, product_id="PROD-COGS01")
        result = compute_cogs_report(prop_id=1, period="month", method="lifo")
        row = result["items"][0]
        assert row["cogs"] == 45.00
        breakdown = row["layer_breakdown"]
        assert len(breakdown) == 1
        assert breakdown[0]["units_consumed"] == 15.0
        assert breakdown[0]["cost_per_unit"] == 3.00

    def test_approx_method_uses_cost_price_snapshot(self, db, two_fifo_layers):
        """``approx`` bypasses layers; cost = units × cost_price."""
        _seed_booking_with_lines(db, units=5, product_id="PROD-COGS01")
        result = compute_cogs_report(prop_id=1, period="month", method="approx")
        row = result["items"][0]
        # 5 × cost_price(=2.00) = 10.00
        assert row["cogs"] == 10.00
        assert row["avg_unit_cost"] == 2.00
        # Layers untouched.
        layers = list(db.fact_inventory.find(
            {"product_id": "PROD-COGS01"},
        ))
        assert len(layers) == 2
        for layer in layers:
            assert float(layer["qty_remaining"]) == layer["qty_initial"]
            assert layer["is_active"] is True

    def test_unknown_method_raises(self, db):
        _seed_product(db)
        _seed_booking_with_lines(db)
        with pytest.raises(ValueError):
            # ``compute_cogs_report`` delegates string validation to the
            # pipeline pattern Pydantic enforcement upstream; here we test
            # the service-level guard inside ``drain_layers_for_sale``.
            from src.app.modules.partner.services._inventory import (
                drain_layers_for_sale,
            )
            drain_layers_for_sale(
                prop_id=1, product_id="PROD-COGS01",
                units_to_drain=5.0, method="wat",
            )


class TestComputeCogsFallbackAggregation:
    def test_fallback_units_summed_across_products(self, db):
        """Two products, each drains more than layers allow → summed in summary."""
        # Product A: 1 layer of 5, sells 8 → fallback 3
        _seed_product(db, product_id="PROD-A", cost_price=2.00)
        insert_inventory_layer(
            prop_id=1, product_id="PROD-A",
            qty=5.0, cost_per_unit=1.00, source="opening_stock",
        )
        _seed_booking_with_lines(
            db, booking_id="BK-A", product_id="PROD-A",
            units=8, name="Prod A",
        )
        # Product B: 1 layer of 2, sells 7 → fallback 5
        _seed_product(db, product_id="PROD-B", cost_price=4.00)
        insert_inventory_layer(
            prop_id=1, product_id="PROD-B",
            qty=2.0, cost_per_unit=2.00, source="opening_stock",
        )
        _seed_booking_with_lines(
            db, booking_id="BK-B", product_id="PROD-B",
            units=7, name="Prod B",
        )
        result = compute_cogs_report(prop_id=1, period="month", method="fifo")
        assert result["summary"]["fallback_units_across_products"] == 8  # 3 + 5
        assert result["summary"]["distinct_products_sold"] == 2


class TestComputeCogsLineItems:
    def test_line_item_without_product_id_is_ignored(self, db, month_start_anchor):
        """Manual room charges have ``product_id=None`` and should be filtered out."""
        _seed_product(db, product_id="PROD-VALID")
        _seed_booking_with_lines(
            db, booking_id="BK-VALID",
            product_id="PROD-VALID", units=5,
            added_at=month_start_anchor + timedelta(days=2),
        )
        # Manual line item with no product_id.
        db.booking_orders.insert_one({
            "booking_id": "BK-MANUAL",
            "prop_id": 1,
            "status": "confirmed",
            "line_items": [{
                "item_id": "LI-MANUAL-1",
                "product_id": None,
                "name": "Manual room charge",
                "quantity": 1,
                "unit_price": 100.0,
                "total": 100.0,
                "added_at": month_start_anchor + timedelta(days=2),
                "added_by": "system",
            }],
            "total_charges": 100.0,
        })
        result = compute_cogs_report(prop_id=1, period="month", method="approx")
        # Only the catalog-backed item contributes.
        assert result["summary"]["units_sold"] == 5
        assert result["summary"]["distinct_products_sold"] == 1


class TestComputeCogsPersistence:
    def test_persistent_drain_reduces_remaining_supply(self, db, two_fifo_layers):
        """Successive reports with FIFO persist should drain layers over time.

        With ``two_fifo_layers`` (10 @ $1.00 oldest + 20 @ $3.00 newest),
        draining 12 units FIFO consumes:
          - 10 from layer 1 @ $1.00 = $10.00
          - 2 from layer 2 @ $3.00  = $6.00
        Total COGS = $16.00.

        After the report, ``qty_remaining`` across both layers should
        sum to 30 - 12 = 18.
        """
        _seed_booking_with_lines(
            db, units=12, product_id="PROD-COGS01",
        )
        first = compute_cogs_report(prop_id=1, period="month", method="fifo")
        assert first["items"][0]["cogs"] == pytest.approx(16.00, abs=0.01)

        # After the first report the layers should be partially drained.
        layer_remaining = db.fact_inventory.find(
            {"product_id": "PROD-COGS01"},
        )
        total_remaining = sum(
            float(layer["qty_remaining"]) for layer in layer_remaining
        )
        # 30 initial - 12 consumed = 18 remaining.
        assert total_remaining == pytest.approx(18.0, abs=0.01)


# NOTE: any per-file cleanup needed beyond conftest's autouse
# ``_clean_collections`` is intentionally not added here — the 6 new
# collections were registered there to keep isolation uniform across the
# entire suite.
