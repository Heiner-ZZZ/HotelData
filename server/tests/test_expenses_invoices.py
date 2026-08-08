"""Tests for expense invoice creation with auto-restock product lines.

Feature: registering a purchase invoice can include product lines that
immediately restock inventory (qty += , cost_price update, fact_inventory
layer + DR 1050 / CR 2010 ledger entry) in a single step, with the
invoice id as the real FK on each restock.

Also covers the multi-status filter on ``list_invoices`` (CSV status → $in)
so invoice pickers can exclude rejected invoices as purchase sources.
"""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
import pytest
from fastapi import HTTPException

from src.app.modules.expenses.routes import create_invoice, get_invoice, list_invoices
from src.app.modules.expenses.schemas import InvoiceCreate


def _seed_product(
    db,
    *,
    prop_id: int = 1,
    name: str = "Agua Mineral",
    cost_price: float = 1.50,
    unit_price: float = 3.00,
    quantity_available: int = 5,
    product_id: str = "PROD-AGUA01",
) -> str:
    db.hotel_products.insert_one({
        "prop_id": prop_id,
        "product_id": product_id,
        "name": name,
        "description": "Botella 500ml",
        "unit_price": float(unit_price),
        "quantity_available": int(quantity_available),
        "cost_price": float(cost_price),
        "category": "Bebidas",
        "type": "retail",
        "is_active": True,
        "created_by": "test_seed",
        "created_at": datetime.now(timezone.utc),
    })
    return product_id


def _dump(result) -> dict:
    """Routes return Pydantic models (extra="allow") — flatten for dict-style asserts."""
    return result.model_dump()


def _fake_request() -> object:
    """Minimal Request stand-in satisfying the audit calls in get_invoice."""
    from types import SimpleNamespace
    return SimpleNamespace(
        url="http://test/api/expenses/invoices/x",
        state=SimpleNamespace(current_user={"username": "admin_test"}),
    )


def _base_payload(**overrides) -> dict:
    payload = {
        "vendor_name": "Distribuidora Lima",
        "category": "Suministros",
        "description": "Compra mensual",
        "amount": 100.0,
        "tax_amount": 0.0,
        "invoice_date": "2026-08-01",
        "due_date": "2026-09-01",
        "notes": "",
        "prop_id": 1,
    }
    payload.update(overrides)
    return payload


class TestCreateInvoiceWithProductLines:
    def test_restocks_stock_and_links_invoice(self, db):
        """One line → stock increases, layer + FK point at the new invoice."""
        _seed_product(db)
        payload = InvoiceCreate(**_base_payload(product_lines=[
            {"product_id": "PROD-AGUA01", "qty": 3.0, "unit_cost": 2.10},
        ]))

        result = _dump(create_invoice(payload=payload, current_user={"username": "admin_test"}))

        assert result["amount"] == 6.30  # recomputed from the line, not 100
        assert result["total"] == 6.30
        assert len(result["product_lines"]) == 1
        line = result["product_lines"][0]
        assert line["product_id"] == "PROD-AGUA01"
        assert line["name"] == "Agua Mineral"
        assert line["qty"] == 3.0
        assert line["unit_cost"] == 2.10
        assert line["line_total"] == 6.30
        assert line["restocked"] is True

        # Stock incremented 5 → 8.
        stored = db.hotel_products.find_one({"prop_id": 1, "product_id": "PROD-AGUA01"})
        assert stored["quantity_available"] == 8
        # The restock FK points at the new invoice.
        assert stored["last_purchase_invoice_ref"] == result["id"]

        # fact_inventory layer carries the same link.
        layer = db.fact_inventory.find_one({"prop_id": 1, "product_id": "PROD-AGUA01"})
        assert layer is not None
        assert layer["invoice_ref"] == result["id"]
        assert layer["qty_initial"] == 3.0

        # The invoice doc itself stores the lines for traceability, with the
        # persisted restock outcome.
        raw = db.expense_invoices.find_one({"_id": ObjectId(result["id"])})
        assert raw["product_lines"] == [
            {"product_id": "PROD-AGUA01", "name": "Agua Mineral",
             "qty": 3.0, "unit_cost": 2.10, "line_total": 6.30, "restocked": True}
        ]

    def test_amount_recomputed_from_lines(self, db):
        """A mismatched payload.amount must not win over the line sum."""
        _seed_product(db)
        payload = InvoiceCreate(**_base_payload(
            amount=999.0,
            product_lines=[{"product_id": "PROD-AGUA01", "qty": 2.0, "unit_cost": 5.0}],
        ))
        result = _dump(create_invoice(payload=payload, current_user={"username": "admin_test"}))
        assert result["amount"] == 10.0

    def test_rejects_unknown_product_without_writing(self, db):
        """An unknown product → 400 and NO invoice or stock side effects."""
        payload = InvoiceCreate(**_base_payload(product_lines=[
            {"product_id": "PROD-NOPE", "qty": 1.0, "unit_cost": 2.0},
        ]))
        with pytest.raises(HTTPException) as exc_info:
            create_invoice(payload=payload, current_user={"username": "admin_test"})
        assert exc_info.value.status_code == 400
        assert db.expense_invoices.count_documents({}) == 0
        assert db.fact_inventory.count_documents({}) == 0

    def test_without_lines_keeps_manual_amount(self, db):
        """Regression: no lines → amount stays the manual value, no restock."""
        payload = InvoiceCreate(**_base_payload())
        result = _dump(create_invoice(payload=payload, current_user={"username": "admin_test"}))
        assert result["amount"] == 100.0
        assert not result.get("product_lines")
        assert db.fact_inventory.count_documents({}) == 0

    def test_rejects_missing_prop_id_with_lines(self, db):
        """Auto-restock needs a hotel; a line without prop_id → 400, no writes."""
        payload = InvoiceCreate(**_base_payload(prop_id=None, product_lines=[
            {"product_id": "PROD-AGUA01", "qty": 1.0, "unit_cost": 2.0},
        ]))
        with pytest.raises(HTTPException) as exc_info:
            create_invoice(payload=payload, current_user={"username": "admin_test"})
        assert exc_info.value.status_code == 400
        assert db.expense_invoices.count_documents({}) == 0


class TestGetInvoiceLinkedRestocks:
    def test_detail_includes_product_lines_with_live_stock(self, db):
        """get_invoice returns the restocked lines enriched with the product's
        current stock/cost so the detail view can show the reverse link."""
        _seed_product(db, quantity_available=5, cost_price=1.50)
        created = _dump(create_invoice(
            payload=InvoiceCreate(**_base_payload(product_lines=[
                {"product_id": "PROD-AGUA01", "qty": 3.0, "unit_cost": 2.10},
            ])),
            current_user={"username": "admin_test"},
        ))

        detail = _dump(get_invoice(request=_fake_request(), invoice_id=created["id"]))

        lines = detail["product_lines"]
        assert len(lines) == 1
        line = lines[0]
        assert line["product_id"] == "PROD-AGUA01"
        assert line["name"] == "Agua Mineral"
        assert line["qty"] == 3.0
        assert line["unit_cost"] == 2.10
        assert line["line_total"] == 6.30
        assert line["restocked"] is True
        # Live enrichment — stock went 5 → 8, cost updated to the line cost.
        assert line["stock_now"] == 8
        assert line["cost_now"] == 2.10

    def test_detail_without_lines_omits_section_data(self, db):
        """Invoices without product lines carry no linked restocks."""
        created = _dump(create_invoice(
            payload=InvoiceCreate(**_base_payload()),
            current_user={"username": "admin_test"},
        ))
        detail = _dump(get_invoice(request=_fake_request(), invoice_id=created["id"]))
        assert detail.get("product_lines") in (None, [])

    def test_detail_line_survives_deleted_product(self, db):
        """If the product is deleted meanwhile, the line stays visible with
        null live fields instead of crashing."""
        _seed_product(db)
        created = _dump(create_invoice(
            payload=InvoiceCreate(**_base_payload(product_lines=[
                {"product_id": "PROD-AGUA01", "qty": 2.0, "unit_cost": 4.0},
            ])),
            current_user={"username": "admin_test"},
        ))
        db.hotel_products.delete_many({"prop_id": 1, "product_id": "PROD-AGUA01"})

        detail = _dump(get_invoice(request=_fake_request(), invoice_id=created["id"]))
        line = detail["product_lines"][0]
        assert line["product_id"] == "PROD-AGUA01"
        assert line["stock_now"] is None
        assert line["cost_now"] is None


class TestListInvoicesStatusFilter:
    """Multi-status CSV filter so invoice pickers exclude rejected invoices."""

    def _seed_invoice(self, db, vendor: str, status: str) -> str:
        result = db.expense_invoices.insert_one({
            "vendor_name": vendor, "category": "Suministros",
            "amount": 10.0, "tax_amount": 0.0, "total": 10.0,
            "status": status, "invoice_date": "2026-08-01",
            "due_date": "2026-09-01", "notes": "", "prop_id": 1,
            "created_at": datetime.now(timezone.utc),
        })
        return str(result.inserted_id)

    def test_status_csv_filters_to_allowed_states(self, db):
        """status=pending,approved,paid returns only those — never rejected."""
        self._seed_invoice(db, "Pendiente SA", "pending")
        self._seed_invoice(db, "Aprobada SA", "approved")
        self._seed_invoice(db, "Pagada SA", "paid")
        self._seed_invoice(db, "Rechazada SA", "rejected")

        result = list_invoices(
            request=_fake_request(),
            status_filter="pending,approved,paid",
            category=None,
            category_id=None,
            vendor=None,
            prop_id=1,
            page=1,
            page_size=50,
        )
        vendors = {i.vendor_name for i in result.items}
        assert "Rechazada SA" not in vendors
        assert vendors == {"Pendiente SA", "Aprobada SA", "Pagada SA"}

    def test_status_single_value_still_works(self, db):
        """Backward compat: a plain status string keeps matching exactly."""
        self._seed_invoice(db, "Pendiente SA", "pending")
        self._seed_invoice(db, "Aprobada SA", "approved")

        result = list_invoices(
            request=_fake_request(),
            status_filter="pending",
            category=None,
            category_id=None,
            vendor=None,
            prop_id=1,
            page=1,
            page_size=50,
        )
        vendors = {i.vendor_name for i in result.items}
        assert vendors == {"Pendiente SA"}
