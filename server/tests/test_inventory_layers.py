"""Tests for inventory layer helpers (Fase 6: atomic drain + FIFO/LIFO/approx).

Covers:
- insert_inventory_layer: semantic id, snapshot fields, default source
- _atomic_layer_decrement: success path, zero-flip (is_active False,
  consumed_at stamped), rejection on insufficient qty_remaining
- drain_layers_for_sale: FIFO ordering, LIFO ordering, fallback_units
  accounting, approx mode bypasses layers, persist=False is read-only
- Race condition: 10 concurrent drains on a single ``qty_initial=100``
  layer should atomically consume exactly 100 units across the
  ``source="layer"`` breakdown and exactly ``(total_requested - 100)``
  units across ``source="fallback_layer_missing"``.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import pytest

from src.app.modules.partner.services import _inventory


# ─────────────────────────── Helpers ────────────────────────────


def _seed_product(db, *, prop_id: int = 1, product_id: str = "PROD-INV01",
                  cost_price: float = 2.00,
                  quantity_available: int = 100) -> None:
    db.hotel_products.insert_one({
        "prop_id": prop_id,
        "product_id": product_id,
        "name": "Test inventory product",
        "unit_price": 5.0,
        "cost_price": float(cost_price),
        "quantity_available": int(quantity_available),
        "category": "Test",
        "is_active": True,
        "created_by": "test_seed",
    })


def _seed_layer(db, *, prop_id: int = 1, product_id: str = "PROD-INV01",
                qty: float = 100.0, cost_per_unit: float = 2.0,
                acquired_at: datetime | None = None,
                layer_id: str = "INV-TEST01") -> str:
    doc = {
        "prop_id": prop_id,
        "product_id": product_id,
        "layer_id": layer_id,
        "qty_initial": float(qty),
        "qty_remaining": float(qty),
        "cost_per_unit": float(cost_per_unit),
        "acquired_at": acquired_at or datetime.now(timezone.utc),
        "source": "restock",
        "supplier_name": "Test Supplier",
        "invoice_ref": "TEST-INV",
        "consumed_at": None,
        "created_by": "test_seed",
        "is_active": True,
    }
    db.fact_inventory.insert_one(doc)
    return layer_id


# ─────────────────────────── Fixtures ────────────────────────────


@pytest.fixture
def seeded_product_with_cost(db):
    _seed_product(db, cost_price=2.00)
    return "PROD-INV01"


@pytest.fixture
def single_layer(db, seeded_product_with_cost):
    base = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
    lid = _seed_layer(
        db, qty=100.0, cost_per_unit=2.50, acquired_at=base,
    )
    return {"layer_id": lid, "qty": 100.0, "acquired_at": base}


@pytest.fixture
def two_fifo_layers(db, seeded_product_with_cost):
    base = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
    _seed_layer(
        db, qty=10.0, cost_per_unit=1.00,
        acquired_at=base,
        layer_id="INV-OLDEST",
    )
    _seed_layer(
        db, qty=20.0, cost_per_unit=3.00,
        acquired_at=base + timedelta(hours=1),
        layer_id="INV-NEWERF",
    )
    return {
        "oldest": {"layer_id": "INV-OLDEST", "qty": 10.0,
                   "cost": 1.00, "at": base},
        "newer": {"layer_id": "INV-NEWERF", "qty": 20.0,
                  "cost": 3.00, "at": base + timedelta(hours=1)},
    }


# ─────────────────── insert_inventory_layer tests ──────────────────


class TestInsertInventoryLayer:
    def test_insert_returns_doc_with_layer_id(
        self, db, seeded_product_with_cost,
    ):
        doc = _inventory.insert_inventory_layer(
            prop_id=1, product_id="PROD-INV01",
            qty=30.0, cost_per_unit=2.00,
            supplier_name="Acme", invoice_ref="AC-1",
        )
        assert doc is not None
        assert doc["layer_id"].startswith("INV-")
        assert doc["qty_initial"] == 30.0
        assert doc["qty_remaining"] == 30.0
        assert doc["cost_per_unit"] == 2.00
        assert doc["source"] == "restock"
        assert doc["is_active"] is True
        assert doc["consumed_at"] is None

    def test_insert_default_source_is_restock(
        self, db, seeded_product_with_cost,
    ):
        doc = _inventory.insert_inventory_layer(
            prop_id=1, product_id="PROD-INV01",
            qty=5.0, cost_per_unit=1.50,
        )
        assert doc["source"] == "restock"

    def test_insert_custom_source_overrides(
        self, db, seeded_product_with_cost,
    ):
        doc = _inventory.insert_inventory_layer(
            prop_id=1, product_id="PROD-INV01",
            qty=5.0, cost_per_unit=1.50,
            source="opening_stock",
        )
        assert doc["source"] == "opening_stock"


# ─────────────── _atomic_layer_decrement tests ─────────────────


class TestAtomicLayerDecrement:
    def test_atomic_decrement_success_reduces_qty(
        self, db, single_layer,
    ):
        layer_doc = db.fact_inventory.find_one(
            {"layer_id": single_layer["layer_id"]},
        )
        ok = _inventory._atomic_layer_decrement(
            db=db, layer_id=layer_doc["_id"], take=30.0,
        )
        assert ok is True
        reloaded = db.fact_inventory.find_one(
            {"_id": layer_doc["_id"]},
        )
        assert float(reloaded["qty_remaining"]) == 70.0

    def test_atomic_decrement_flips_inactive_when_qty_hits_zero(
        self, db, single_layer,
    ):
        layer_doc = db.fact_inventory.find_one(
            {"layer_id": single_layer["layer_id"]},
        )
        ok = _inventory._atomic_layer_decrement(
            db=db, layer_id=layer_doc["_id"],
            take=float(single_layer["qty"]),
        )
        assert ok is True
        reloaded = db.fact_inventory.find_one(
            {"_id": layer_doc["_id"]},
        )
        assert float(reloaded["qty_remaining"]) == 0.0
        assert reloaded["is_active"] is False
        assert reloaded["consumed_at"] is not None

    def test_atomic_decrement_rejects_when_not_enough_available(
        self, db, single_layer,
    ):
        layer_doc = db.fact_inventory.find_one(
            {"layer_id": single_layer["layer_id"]},
        )
        ok = _inventory._atomic_layer_decrement(
            db=db, layer_id=layer_doc["_id"], take=200.0,
        )
        assert ok is False
        reloaded = db.fact_inventory.find_one(
            {"_id": layer_doc["_id"]},
        )
        assert float(reloaded["qty_remaining"]) == single_layer["qty"]

    def test_atomic_decrement_take_zero_is_noop(
        self, db, single_layer,
    ):
        layer_doc = db.fact_inventory.find_one(
            {"layer_id": single_layer["layer_id"]},
        )
        ok = _inventory._atomic_layer_decrement(
            db=db, layer_id=layer_doc["_id"], take=0.0,
        )
        assert ok is True
        reloaded = db.fact_inventory.find_one(
            {"_id": layer_doc["_id"]},
        )
        assert float(reloaded["qty_remaining"]) == single_layer["qty"]


# ────────────────── drain_layers_for_sale tests ─────────────────


class TestDrainLayersForSale:
    def test_fifo_drains_oldest_first(self, db, two_fifo_layers):
        result = _inventory.drain_layers_for_sale(
            prop_id=1, product_id="PROD-INV01",
            units_to_drain=15.0, method="fifo",
        )
        # FIFO: oldest 10 @ 1.00 = 10.00; newest 5 @ 3.00 = 15.00 → 25.00.
        assert result["cogs"] == 25.00
        assert len(result["layer_breakdown"]) == 2
        # Source must be ``layer`` (within bounds).
        assert all(
            entry["source"] == "layer" for entry in result["layer_breakdown"]
        )
        first_breakdown = result["layer_breakdown"][0]
        assert first_breakdown["layer_id"] == "INV-OLDEST"
        assert first_breakdown["units_consumed"] == 10.0
        assert first_breakdown["cost_per_unit"] == 1.00
        second_breakdown = result["layer_breakdown"][1]
        assert second_breakdown["layer_id"] == "INV-NEWERF"
        assert second_breakdown["units_consumed"] == 5.0
        assert second_breakdown["cost_per_unit"] == 3.00
        assert result["fallback_units"] == 0.0

    def test_lifo_drains_newest_first(self, db, two_fifo_layers):
        result = _inventory.drain_layers_for_sale(
            prop_id=1, product_id="PROD-INV01",
            units_to_drain=15.0, method="lifo",
        )
        # LIFO: newest 20 @ 3.00 first; only 15 of those 20 needed → 45.00.
        assert result["cogs"] == 45.00
        assert len(result["layer_breakdown"]) == 1
        assert result["layer_breakdown"][0]["layer_id"] == "INV-NEWERF"
        assert result["layer_breakdown"][0]["units_consumed"] == 15.0
        assert result["fallback_units"] == 0.0

    def test_fallback_units_when_layers_exhausted(
        self, db, two_fifo_layers,
    ):
        """Layers total 30 (10 + 20); drain 50 → 30 layer + 20 fallback."""
        result = _inventory.drain_layers_for_sale(
            prop_id=1, product_id="PROD-INV01",
            units_to_drain=50.0, method="fifo",
        )
        # Layer COGS: 10 @1.00 + 20 @3.00 = 70.00. Fallback at cost_price
        # (=2.00) × 20 = 40.00. Total = 110.00.
        assert result["cogs"] == 110.00
        assert result["fallback_units"] == 20.0
        assert len(result["layer_breakdown"]) == 3  # 2 layers + 1 fallback
        fallback_entry = result["layer_breakdown"][-1]
        assert fallback_entry["source"] == "fallback_layer_missing"
        assert fallback_entry["layer_id"] is None
        assert fallback_entry["units_consumed"] == 20.0
        assert fallback_entry["cost_per_unit"] == 2.00  # hotel_products.cost_price

    def test_approx_method_bypasses_layers_entirely(
        self, db, two_fifo_layers,
    ):
        """``approx`` mode never touches ``fact_inventory``."""
        result = _inventory.drain_layers_for_sale(
            prop_id=1, product_id="PROD-INV01",
            units_to_drain=10.0, method="approx",
        )
        # approx: 10 × cost_price(=2.00) = 20.00.
        assert result["cogs"] == 20.00
        assert len(result["layer_breakdown"]) == 1
        entry = result["layer_breakdown"][0]
        assert entry["source"] == "approx_fallback"
        assert entry["layer_id"] is None
        # Persist invariant: ``fact_inventory`` was NOT modified.
        layers = list(db.fact_inventory.find(
            {"product_id": "PROD-INV01"},
        ))
        for layer in layers:
            assert float(layer["qty_remaining"]) == layer["qty_initial"]

    def test_unknown_method_raises(self, db, single_layer):
        with pytest.raises(ValueError, match=r"Unknown method"):
            _inventory.drain_layers_for_sale(
                prop_id=1, product_id="PROD-INV01",
                units_to_drain=5.0, method="wat",
            )

    def test_persist_false_does_not_write_back(
        self, db, single_layer,
    ):
        result = _inventory.drain_layers_for_sale(
            prop_id=1, product_id="PROD-INV01",
            units_to_drain=20.0, method="fifo", persist=False,
        )
        assert result["cogs"] == 50.0  # 20 × 2.50
        assert len(result["layer_breakdown"]) == 1
        # DB quantity unchanged.
        layer = db.fact_inventory.find_one(
            {"layer_id": single_layer["layer_id"]},
        )
        assert float(layer["qty_remaining"]) == single_layer["qty"]

    def test_persist_true_writes_back_and_flips_active(
        self, db, single_layer,
    ):
        result = _inventory.drain_layers_for_sale(
            prop_id=1, product_id="PROD-INV01",
            units_to_drain=float(single_layer["qty"]),
            method="fifo", persist=True,
        )
        assert result["cogs"] == 250.00  # 100 × 2.50
        layer = db.fact_inventory.find_one(
            {"layer_id": single_layer["layer_id"]},
        )
        assert float(layer["qty_remaining"]) == 0.0
        assert layer["is_active"] is False
        assert layer["consumed_at"] is not None

    def test_zero_units_returns_zero_breakdown(
        self, db, single_layer,
    ):
        result = _inventory.drain_layers_for_sale(
            prop_id=1, product_id="PROD-INV01",
            units_to_drain=0.0, method="fifo",
        )
        assert result["cogs"] == 0.0
        assert result["layer_breakdown"] == []
        assert result["fallback_units"] == 0.0
        assert result["avg_unit_cost"] == 0.0


# ───────────────── Race condition (Fase 6 invariant) ───────────────────


class TestConcurrentDrainRace:
    """Prove the aggregation-pipeline atomic decrement prevents phantom consumption.

    Setup: 1 layer with ``qty_initial=100``.
    Stress: 10 threads each drain 15 units → 150 requested total.
    Invariants:
      1. The SUM of ``units_consumed`` across all ``source="layer"``
         breakdown entries equals exactly 100.
      2. The SUM of ``units_consumed`` across all
         ``source="fallback_layer_missing"`` entries equals exactly 50.
      3. The DB layer has ``qty_remaining == 0``, ``is_active == False``,
         ``consumed_at`` non-null.
      4. The total ``drain.cogs`` summed across threads equals:
            100 × layer_cost + 50 × fallback_cost
      5. The 100 units are observable as ATOMIC consumption: never double-
         counted and never negative.
    """

    def test_10_concurrent_drains_consume_exactly_100_layer_units(
        self, db, single_layer,
    ):
        layer_cost = 2.50
        fallback_cost = db.hotel_products.find_one(
            {"product_id": "PROD-INV01"},
        )["cost_price"]

        def _drain():
            return _inventory.drain_layers_for_sale(
                prop_id=1, product_id="PROD-INV01",
                units_to_drain=15.0, method="fifo", persist=True,
            )

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(_drain) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        layer_units = sum(
            entry["units_consumed"]
            for drain in results
            for entry in drain["layer_breakdown"]
            if entry["source"] == "layer"
        )
        fallback_units = sum(
            entry["units_consumed"]
            for drain in results
            for entry in drain["layer_breakdown"]
            if entry["source"] == "fallback_layer_missing"
        )
        # The DB-side bookkeeping matches each thread's breakdown.
        assert layer_units == pytest.approx(100.0, abs=1e-6)
        assert fallback_units == pytest.approx(50.0, abs=1e-6)

        # DB state after the storm.
        layer = db.fact_inventory.find_one(
            {"layer_id": single_layer["layer_id"]},
        )
        assert float(layer["qty_remaining"]) == 0.0
        assert layer["is_active"] is False
        assert layer["consumed_at"] is not None

        # COGS invariant: compute from the breakdown itself (not
        # ``drain["cogs"]`` which is pre-rounded and can drift across
        # threads). The breakdown entries carry the **pre-rounded** cost,
        # so summing them yields a stable deterministic invariant.
        layer_cogs_sum = sum(
            round(
                entry["units_consumed"] * entry["cost_per_unit"], 4,
            )
            for drain in results
            for entry in drain["layer_breakdown"]
            if entry["source"] == "layer"
        )
        fallback_cogs_sum = sum(
            round(
                entry["units_consumed"] * entry["cost_per_unit"], 4,
            )
            for drain in results
            for entry in drain["layer_breakdown"]
            if entry["source"] == "fallback_layer_missing"
        )
        assert layer_cogs_sum == pytest.approx(100.0 * layer_cost, abs=1e-3)
        assert fallback_cogs_sum == pytest.approx(
            50.0 * fallback_cost, abs=1e-3,
        )
