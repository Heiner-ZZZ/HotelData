"""Tests for hotel_products service (Fase 4: restock + cost_price + inventory).

Covers:
- restock increments quantity_available and overwrites cost_price
- restock inserts a fact_inventory layer (Fase 6 wiring)
- restock returns fact_inventory_layer_id for UI traceability
- restock is best-effort: ledger failure does NOT roll back stock
- restock validates qty > 0 and unit_cost >= 0
- restock returns None for unknown (prop_id, product_id)
- list_hotel_products sorts by category then name
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.app.modules.partner.services import hotel_products


# ───────────────────────────── Helpers ─────────────────────────────


def _seed_product(
    db,
    *,
    prop_id: int = 1,
    name: str = "Agua Mineral",
    cost_price: float = 1.50,
    unit_price: float = 3.00,
    quantity_available: int = 5,
    category: str = "Bebidas",
    product_id: str = "PROD-AGUA01",
) -> str:
    """Insert a baseline hotel_product fixture and return its product_id."""
    db.hotel_products.insert_one({
        "prop_id": prop_id,
        "product_id": product_id,
        "name": name,
        "description": "Botella 500ml",
        "unit_price": float(unit_price),
        "quantity_available": int(quantity_available),
        "cost_price": float(cost_price),
        "category": category,
        "type": "retail",
        "is_active": True,
        "created_by": "test_seed",
        "created_at": datetime.now(timezone.utc),
    })
    return product_id


def _active_fact_inventory_layer_count(db, prop_id: int, product_id: str) -> int:
    """Count open layers in ``fact_inventory`` for the given product."""
    return db.fact_inventory.count_documents({
        "prop_id": prop_id,
        "product_id": product_id,
        "is_active": True,
        "qty_remaining": {"$gt": 0},
    })


# ─────────────────────────── Fixtures ────────────────────────────


@pytest.fixture
def seeded_product(db):
    return _seed_product(db)


@pytest.fixture
def seeded_two_products(db):
    """Two products in the same hotel for sorting tests."""
    _seed_product(
        db, name="Snack Bar", category="Snacks",
        product_id="PROD-SNACK1", quantity_available=10,
    )
    _seed_product(
        db, name="Agua Mineral", category="Bebidas",
        product_id="PROD-AGUA02", quantity_available=20,
    )


# ─────────────────────────── Tests ────────────────────────────


class TestListHotelProducts:
    def test_list_empty_hotel_returns_empty_list(self, db):
        assert hotel_products.list_hotel_products(prop_id=999) == []

    def test_list_returns_seeded_product(self, db, seeded_product):
        items = hotel_products.list_hotel_products(prop_id=1)
        assert len(items) == 1
        item = items[0]
        assert item["product_id"] == "PROD-AGUA01"
        assert item["name"] == "Agua Mineral"
        # ``_id`` is stripped by projection (list_hotel_products uses {``_id:`` 0}).
        assert "_id" not in item
        assert "id" not in item  # docs stay in catalog shape, not wire shape

    def test_list_sorts_by_category_then_name(self, db, seeded_two_products):
        items = hotel_products.list_hotel_products(prop_id=1)
        assert len(items) == 2
        # Bebidas < Snacks lexicographically; within Bebidas there's only one.
        assert [it["category"] for it in items] == ["Bebidas", "Snacks"]


class TestRestockProduct:
    def test_restock_increments_quantity_and_overwrites_cost(
        self, db, seeded_product,
    ):
        result = hotel_products.restock_product(
            prop_id=1,
            product_id="PROD-AGUA01",
            qty=3.0,
            unit_cost=2.10,
            supplier_name="Distribuidora Lima",
            invoice_ref="INV-001",
            changed_by="admin_test",
        )
        assert result is not None
        # old qty 5 + 3 = 8
        assert result["quantity_available"] == 8
        # cost updated to latest purchase price (last-purchase model)
        assert result["cost_price"] == 2.10
        assert result["default_supplier"] == "Distribuidora Lima"
        assert result["last_purchase_invoice_ref"] == "INV-001"
        assert result["product_id"] == "PROD-AGUA01"
        assert result["prop_id"] == 1

    def test_restock_persists_to_database(self, db, seeded_product):
        hotel_products.restock_product(
            prop_id=1, product_id="PROD-AGUA01",
            qty=10.0, unit_cost=2.00, changed_by="admin_test",
        )
        stored = db.hotel_products.find_one(
            {"prop_id": 1, "product_id": "PROD-AGUA01"},
        )
        assert stored is not None
        assert stored["quantity_available"] == 15  # 5 + 10
        assert stored["cost_price"] == 2.00

    def test_restock_inserts_fact_inventory_layer(
        self, db, seeded_product,
    ):
        assert _active_fact_inventory_layer_count(db, 1, "PROD-AGUA01") == 0
        hotel_products.restock_product(
            prop_id=1, product_id="PROD-AGUA01",
            qty=20.0, unit_cost=1.80,
            supplier_name="Acme Supply",
            invoice_ref="AC-12345",
            changed_by="admin_test",
        )
        layers = list(db.fact_inventory.find(
            {"prop_id": 1, "product_id": "PROD-AGUA01"},
        ))
        assert len(layers) == 1
        layer = layers[0]
        assert layer["qty_initial"] == 20.0
        assert layer["qty_remaining"] == 20.0
        assert layer["cost_per_unit"] == 1.80
        assert layer["source"] == "restock"
        assert layer["supplier_name"] == "Acme Supply"
        assert layer["invoice_ref"] == "AC-12345"
        assert layer["layer_id"].startswith("INV-")

    def test_restock_returns_fact_inventory_layer_id(
        self, db, seeded_product,
    ):
        result = hotel_products.restock_product(
            prop_id=1, product_id="PROD-AGUA01",
            qty=5.0, unit_cost=2.00, changed_by="admin_test",
        )
        assert result is not None
        layer_id = result["fact_inventory_layer_id"]
        assert layer_id != ""
        assert layer_id.startswith("INV-")
        # verify it exists in DB
        stored = db.fact_inventory.find_one({"layer_id": layer_id})
        assert stored is not None
        assert stored["product_id"] == "PROD-AGUA01"

    def test_restock_ledger_failure_does_not_roll_back_stock(
        self, db, seeded_product,
    ):
        """Best-effort: ledger posting raised, stock must still update."""
        with patch(
            "src.app.modules.expenses.service.ledger_hooks.post_journal_entry",
            side_effect=RuntimeError("simulated ledger outage"),
        ):
            result = hotel_products.restock_product(
                prop_id=1, product_id="PROD-AGUA01",
                qty=7.0, unit_cost=2.00, changed_by="admin_test",
            )
        assert result is not None
        assert result["quantity_available"] == 12  # 5 + 7
        assert result["ledger_journal_id"] == ""  # failure

        # DB still saw the stock update.
        stored = db.hotel_products.find_one(
            {"prop_id": 1, "product_id": "PROD-AGUA01"},
        )
        assert stored["quantity_available"] == 12

    def test_restock_audit_failure_does_not_roll_back_stock(
        self, db, seeded_product,
    ):
        """Best-effort: audit row raised, stock must still update."""
        with patch(
            "src.app.modules.partner.services.audit.register_action",
            side_effect=RuntimeError("simulated audit log outage"),
        ):
            result = hotel_products.restock_product(
                prop_id=1, product_id="PROD-AGUA01",
                qty=2.0, unit_cost=1.99, changed_by="admin_test",
            )
        assert result is not None
        assert result["quantity_available"] == 7
        # Layer was still inserted (that's separate from audit).
        assert _active_fact_inventory_layer_count(db, 1, "PROD-AGUA01") == 1

    def test_restock_rejects_qty_zero(self, db, seeded_product):
        with pytest.raises(ValueError, match=r"qty.*>.*0"):
            hotel_products.restock_product(
                prop_id=1, product_id="PROD-AGUA01",
                qty=0.0, unit_cost=2.00, changed_by="admin_test",
            )

    def test_restock_rejects_qty_negative(self, db, seeded_product):
        with pytest.raises(ValueError, match=r"qty.*>.*0"):
            hotel_products.restock_product(
                prop_id=1, product_id="PROD-AGUA01",
                qty=-1.0, unit_cost=2.00, changed_by="admin_test",
            )

    def test_restock_rejects_negative_unit_cost(self, db, seeded_product):
        with pytest.raises(ValueError, match=r"unit_cost.*>=.*0"):
            hotel_products.restock_product(
                prop_id=1, product_id="PROD-AGUA01",
                qty=5.0, unit_cost=-0.01, changed_by="admin_test",
            )

    def test_restock_unknown_product_returns_none(self, db, seeded_product):
        result = hotel_products.restock_product(
            prop_id=1, product_id="PROD-DOES-NOT-EXIST",
            qty=3.0, unit_cost=2.00, changed_by="admin_test",
        )
        assert result is None

    def test_restock_wrong_prop_id_returns_none(self, db):
        # Seed product in prop 999, restock via prop 1.
        _seed_product(db, prop_id=999, product_id="PROD-OTHER")
        result = hotel_products.restock_product(
            prop_id=1, product_id="PROD-OTHER",
            qty=3.0, unit_cost=2.00, changed_by="admin_test",
        )
        assert result is None
