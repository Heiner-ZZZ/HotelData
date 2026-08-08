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

from bson import ObjectId
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


def _seed_expense_invoice(
    db,
    *,
    prop_id: int = 1,
    vendor_name: str = "Acme Supply",
    amount: float = 250.0,
    invoice_id: ObjectId | None = None,
    status: str = "pending",
) -> ObjectId:
    """Insert an expense_invoices fixture and return its ``_id``."""
    doc = {
        "vendor_name": vendor_name,
        "category": "Suministros",
        "description": "Compra de prueba",
        "amount": amount,
        "tax_amount": 0.0,
        "total": amount,
        "status": status,
        "invoice_date": "2026-08-01",
        "due_date": "2026-09-01",
        "notes": "",
        "prop_id": prop_id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    if invoice_id is not None:
        doc["_id"] = invoice_id
    result = db.expense_invoices.insert_one(doc)
    return result.inserted_id


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

    def test_list_resolves_linked_expense_invoice(self, db):
        """An ObjectId last_purchase_invoice_ref is resolved to vendor/date/total."""
        invoice_id = db.expense_invoices.insert_one({
            "vendor_name": "Distribuidora Lima",
            "category": "Suministros",
            "amount": 13.0,
            "tax_amount": 0.0,
            "total": 13.0,
            "status": "pending",
            "invoice_date": "2026-08-06",
            "due_date": "2026-09-06",
            "notes": "",
            "prop_id": 1,
        }).inserted_id
        _seed_product(db, quantity_available=8, cost_price=3.25)
        db.hotel_products.update_one(
            {"prop_id": 1, "product_id": "PROD-AGUA01"},
            {"$set": {"last_purchase_invoice_ref": str(invoice_id)}},
        )

        items = hotel_products.list_hotel_products(prop_id=1)
        assert len(items) == 1
        inv = items[0]["last_purchase_invoice"]
        assert inv is not None
        assert inv["id"] == str(invoice_id)
        assert inv["vendor_name"] == "Distribuidora Lima"
        assert inv["invoice_date"] == "2026-08-06"
        assert inv["total"] == 13.0
        # The raw ref stays untouched (the resolver only enriches).
        assert items[0]["last_purchase_invoice_ref"] == str(invoice_id)

    def test_list_legacy_free_text_ref_returns_none(self, db):
        """Legacy free-text refs (e.g. INV-001) are not links — resolver returns None."""
        _seed_product(db)
        db.hotel_products.update_one(
            {"prop_id": 1, "product_id": "PROD-AGUA01"},
            {"$set": {"last_purchase_invoice_ref": "INV-001"}},
        )
        items = hotel_products.list_hotel_products(prop_id=1)
        assert items[0]["last_purchase_invoice"] is None

    def test_list_dangling_invoice_id_returns_none(self, db):
        """A ref pointing at a deleted invoice resolves to None, not a crash."""
        _seed_product(db)
        db.hotel_products.update_one(
            {"prop_id": 1, "product_id": "PROD-AGUA01"},
            {"$set": {"last_purchase_invoice_ref": str(ObjectId())}},
        )
        items = hotel_products.list_hotel_products(prop_id=1)
        assert items[0]["last_purchase_invoice"] is None

    def test_list_batch_resolves_all_refs_in_single_query(self, db):
        """Multiple linked refs resolve in ONE batched query — no N+1 per product.

        Regression guard for the enrichment refactor: the resolver must not run
        a ``find_one`` per product. It should issue a single ``find`` over the
        valid ObjectId refs (``$in`` + ``prop_id``), leaving ``find_one`` on
        ``expense_invoices`` untouched (0 calls). Cross-property invoices are
        excluded.
        """
        own_a = db.expense_invoices.insert_one({
            "vendor_name": "Distribuidora Lima", "category": "Suministros",
            "amount": 13.0, "tax_amount": 0.0, "total": 13.0,
            "status": "pending", "invoice_date": "2026-08-06",
            "due_date": "2026-09-06", "notes": "", "prop_id": 1,
        }).inserted_id
        own_b = db.expense_invoices.insert_one({
            "vendor_name": "Insumos Andinos", "category": "Suministros",
            "amount": 7.5, "tax_amount": 0.0, "total": 7.5,
            "status": "paid", "invoice_date": "2026-08-02",
            "due_date": "2026-09-02", "notes": "", "prop_id": 1,
        }).inserted_id
        other_prop = db.expense_invoices.insert_one({
            "vendor_name": "Otra Propiedad", "category": "Suministros",
            "amount": 99.0, "tax_amount": 0.0, "total": 99.0,
            "status": "pending", "invoice_date": "2026-08-01",
            "due_date": "2026-09-01", "notes": "", "prop_id": 999,
        }).inserted_id

        # Four products: two linked to prop-1 invoices (one duplicated across
        # products), one to a cross-prop invoice.
        for pid, ref in (
            ("PROD-AGUA01", own_a),
            ("PROD-AGUA02", own_a),  # same invoice as PROD-AGUA01 (duplicate ref)
            ("PROD-SNACK1", own_b),
            ("PROD-CROSS", other_prop),
        ):
            _seed_product(db, product_id=pid, name=f"Producto {pid}")
            db.hotel_products.update_one(
                {"prop_id": 1, "product_id": pid},
                {"$set": {"last_purchase_invoice_ref": str(ref)}},
            )

        # Count find/find_one calls on ANY expense_invoices Collection wrapper
        # (PyMongo builds a fresh Collection per access, so patching the fixture's
        # instance would silently miss the calls made inside the service).
        from pymongo.collection import Collection

        calls = {"find": 0, "find_one": 0}
        original_find = Collection.find
        original_find_one = Collection.find_one

        def _counting_find(self, *args, **kwargs):
            if self.name == "expense_invoices":
                calls["find"] += 1
                # Keep the query for the filter assertion below.
                calls["last_filter"] = args[0] if args else kwargs.get("filter")
            return original_find(self, *args, **kwargs)

        def _counting_find_one(self, *args, **kwargs):
            if self.name == "expense_invoices":
                calls["find_one"] += 1
            return original_find_one(self, *args, **kwargs)

        with patch.object(Collection, "find", _counting_find), \
             patch.object(Collection, "find_one", _counting_find_one):
            items = hotel_products.list_hotel_products(prop_id=1)

        by_id = {it["product_id"]: it for it in items}
        # Contract: exactly ONE batched query — no N+1 of find_one, and no
        # degenerate one-find-per-product either.
        assert calls["find_one"] == 0, "N+1 regression: resolver used find_one per product"
        assert calls["find"] == 1, "batch must resolve all refs in a single find"
        filt = calls.get("last_filter") or {}
        assert "prop_id" in filt, "batch query must keep cross-hotel isolation"
        # Own-prop invoices resolve (duplicate ref → same invoice on both);
        # cross-prop invoice stays None.
        assert by_id["PROD-AGUA01"]["last_purchase_invoice"]["vendor_name"] == "Distribuidora Lima"
        assert by_id["PROD-AGUA02"]["last_purchase_invoice"]["id"] == by_id["PROD-AGUA01"]["last_purchase_invoice"]["id"]
        assert by_id["PROD-SNACK1"]["last_purchase_invoice"]["vendor_name"] == "Insumos Andinos"
        assert by_id["PROD-CROSS"]["last_purchase_invoice"] is None


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

    def test_restock_links_expense_invoice_by_id(
        self, db, seeded_product,
    ):
        """invoice_id resolves the expense invoice and stores its id as the ref."""
        invoice_id = _seed_expense_invoice(db)
        result = hotel_products.restock_product(
            prop_id=1, product_id="PROD-AGUA01",
            qty=3.0, unit_cost=2.10,
            supplier_name="Distribuidora Lima",
            invoice_id=str(invoice_id),
            changed_by="admin_test",
        )
        assert result is not None
        # The id (not free text) is the stored reference.
        assert result["last_purchase_invoice_ref"] == str(invoice_id)

        stored = db.hotel_products.find_one(
            {"prop_id": 1, "product_id": "PROD-AGUA01"},
        )
        assert stored["last_purchase_invoice_ref"] == str(invoice_id)

        # fact_inventory layer carries the same link.
        layer = db.fact_inventory.find_one(
            {"prop_id": 1, "product_id": "PROD-AGUA01"},
        )
        assert layer is not None
        assert layer["invoice_ref"] == str(invoice_id)

    def test_restock_rejects_unknown_invoice_id(self, db, seeded_product):
        """A dangling invoice_id must fail loudly, not store a broken link."""
        with pytest.raises(ValueError, match=r"[Ff]actura"):
            hotel_products.restock_product(
                prop_id=1, product_id="PROD-AGUA01",
                qty=3.0, unit_cost=2.00,
                invoice_id=str(ObjectId()),
                changed_by="admin_test",
            )

    def test_restock_rejects_invoice_from_other_prop(self, db, seeded_product):
        """Invoices belong to a hotel; cross-prop links are rejected."""
        other_invoice_id = _seed_expense_invoice(db, prop_id=999)
        with pytest.raises(ValueError, match=r"[Ff]actura"):
            hotel_products.restock_product(
                prop_id=1, product_id="PROD-AGUA01",
                qty=3.0, unit_cost=2.00,
                invoice_id=str(other_invoice_id),
                changed_by="admin_test",
            )

    def test_restock_rejects_rejected_invoice(self, db, seeded_product):
        """A rejected invoice is not a valid purchase source — no link, no stock.

        Defense-in-depth: the restock modal filters rejected invoices out of
        the selector, but the backend must also refuse a rejected invoice_id
        so a stale/forged link can never back a restock.
        """
        invoice_id = _seed_expense_invoice(db, status="rejected")
        with pytest.raises(ValueError, match=r"[Rr]echazada|rejected"):
            hotel_products.restock_product(
                prop_id=1, product_id="PROD-AGUA01",
                qty=3.0, unit_cost=2.00,
                invoice_id=str(invoice_id),
                changed_by="admin_test",
            )
        # No side effects: stock untouched, no layer.
        stored = db.hotel_products.find_one(
            {"prop_id": 1, "product_id": "PROD-AGUA01"},
        )
        assert stored["quantity_available"] == 5
        assert db.fact_inventory.count_documents({}) == 0

    def test_restock_free_text_ref_still_works(self, db, seeded_product):
        """Backward compatibility: invoice_ref free text keeps working."""
        result = hotel_products.restock_product(
            prop_id=1, product_id="PROD-AGUA01",
            qty=2.0, unit_cost=1.90,
            invoice_ref="INV-MANUAL-77",
            changed_by="admin_test",
        )
        assert result is not None
        assert result["last_purchase_invoice_ref"] == "INV-MANUAL-77"
