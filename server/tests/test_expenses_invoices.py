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

from src.app.modules.expenses.routes import (
    create_invoice,
    delete_invoice,
    get_invoice,
    list_invoices,
    update_invoice,
)
from src.app.modules.expenses.schemas import InvoiceCreate, InvoiceUpdate


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


def test_approved_maintenance_invoice_posts_ap_ledger_and_updates_task(db):
    """Approving a linked maintenance bill creates one AP pair and updates the work order."""
    from src.app.modules.housekeeping.schemas import MaintenanceTaskCreate
    from src.app.modules.housekeeping.service.lifecycle.maintenance import create_maintenance_task

    prop_id = 920
    room_id = "HR-920-101"
    db.dim_hotels.insert_one({"prop_id": prop_id, "display_name": "AP Hotel"})
    db.hotel_rooms.insert_one({
        "hotel_room_id": room_id,
        "prop_id": prop_id,
        "room_label": "101",
        "room_type_id": "standard",
    })
    invoice = _dump(create_invoice(
        payload=InvoiceCreate(**_base_payload(
            prop_id=prop_id,
            amount=125.0,
            tax_amount=0.0,
            category="Mantenimiento",
        )),
        current_user={"username": "admin_test"},
    ))
    task = create_maintenance_task(MaintenanceTaskCreate(
        prop_id=prop_id,
        room_id=room_id,
        task_type="corrective",
        title="Bomba hidráulica",
        actual_cost=125.0,
        expense_invoice_id=invoice["id"],
    ))

    updated = update_invoice(
        invoice_id=invoice["id"],
        prop_id=prop_id,
        payload=InvoiceUpdate(status="approved"),
        current_user={"username": "admin_test"},
    )

    assert updated.status == "approved"
    assert db.ledger_transactions.count_documents({
        "source": "expense_invoice",
        "source_id": invoice["id"],
    }) == 2
    assert db.ledger_transactions.count_documents({
        "source": "expense_invoice",
        "source_id": invoice["id"],
        "account_code": "5030",
        "debit": 125.0,
    }) == 1
    assert db.ledger_transactions.count_documents({
        "source": "expense_invoice",
        "source_id": invoice["id"],
        "account_code": "2010",
        "credit": 125.0,
    }) == 1
    stored_task = db.maintenance_tasks.find_one({"_id": ObjectId(task["id"])})
    assert stored_task["ledger_status"] == "posted"
    assert stored_task["ledger_journal_id"]


def test_approval_posts_effective_updated_amount(db):
    """Approval and amount correction in one request posts the final amount."""
    invoice = _dump(create_invoice(
        payload=InvoiceCreate(**_base_payload(prop_id=923, amount=100.0)),
        current_user={"username": "admin_test"},
    ))

    updated = update_invoice(
        invoice_id=invoice["id"],
        prop_id=923,
        payload=InvoiceUpdate(amount=125.0, status="approved"),
        current_user={"username": "admin_test"},
    )

    assert updated.status == "approved"
    assert db.ledger_transactions.count_documents({
        "source": "expense_invoice",
        "source_id": invoice["id"],
        "account_code": "5030",
        "debit": 125.0,
    }) == 1
    assert db.ledger_transactions.count_documents({
        "source": "expense_invoice",
        "source_id": invoice["id"],
        "account_code": "2010",
        "credit": 125.0,
    }) == 1


def test_product_backed_approval_does_not_duplicate_payable(db):
    """Inventory-backed bills keep their single restock payable pair."""
    _seed_product(db, prop_id=924)
    invoice = _dump(create_invoice(
        payload=InvoiceCreate(**_base_payload(
            prop_id=924,
            amount=999.0,
            product_lines=[{"product_id": "PROD-AGUA01", "qty": 2.0, "unit_cost": 5.0}],
        )),
        current_user={"username": "admin_test"},
    ))
    update_invoice(
        invoice_id=invoice["id"],
        prop_id=924,
        payload=InvoiceUpdate(status="approved"),
        current_user={"username": "admin_test"},
    )
    assert db.ledger_transactions.count_documents({
            "source": "hotel_product_restock",
            "source_id": f"{invoice['id']}:line:0",
        }) == 2

    assert db.ledger_transactions.count_documents({
        "source": "expense_invoice", "source_id": invoice["id"],
    }) == 0


def test_approved_or_paid_expense_invoice_cannot_be_mutated_or_deleted(db):
    """A posted vendor bill requires a compensating document, not in-place edits."""
    invoice = db.expense_invoices.insert_one({
        "vendor_name": "Proveedor protegido",
        "category": "Mantenimiento",
        "description": "Trabajo cerrado",
        "amount": 125.0,
        "tax_amount": 0.0,
        "total": 125.0,
        "status": "paid",
        "prop_id": 921,
        "created_at": datetime.now(timezone.utc),
    }).inserted_id

    with pytest.raises(HTTPException) as update_error:
        update_invoice(
            invoice_id=str(invoice),
            prop_id=921,
            payload=InvoiceUpdate(amount=200.0),
            current_user={"username": "admin_test"},
        )
    assert update_error.value.status_code == 409

    with pytest.raises(HTTPException) as delete_error:
        delete_invoice(invoice_id=str(invoice), prop_id=921, current_user={"username": "admin_test"})
    assert delete_error.value.status_code == 409
    assert db.expense_invoices.count_documents({"_id": invoice}) == 1


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

    def test_existing_restock_retries_missing_ledger_without_incrementing_stock(self, db):
        """A retry repairs AP but does not receive the same goods twice."""
        from src.app.modules.partner.services.hotel_products import restock_product

        _seed_product(db)
        created = _dump(create_invoice(
            payload=InvoiceCreate(**_base_payload(product_lines=[
                {"product_id": "PROD-AGUA01", "qty": 2.0, "unit_cost": 5.0},
            ])),
            current_user={"username": "admin_test"},
        ))
        db.ledger_transactions.delete_many({
            "source": "hotel_product_restock",
            "source_id": f"{created['id']}:line:0",
        })

        restock_product(
            1,
            "PROD-AGUA01",
            qty=2.0,
            unit_cost=5.0,
            supplier_name="Distribuidora Lima",
            invoice_id=created["id"],
            ledger_source_id=f"{created['id']}:line:0",
            inventory_event_id=f"{created['id']}:line:0",
        )

        assert db.hotel_products.find_one({"product_id": "PROD-AGUA01"})["quantity_available"] == 7
        assert db.ledger_transactions.count_documents({
            "source": "hotel_product_restock",
            "source_id": f"{created['id']}:line:0",
        }) == 2

    def test_repeated_product_lines_keep_independent_restock_events(self, db):
        """Two receipt lines for one SKU must not collapse into one layer."""
        _seed_product(db)
        created = _dump(create_invoice(
            payload=InvoiceCreate(**_base_payload(product_lines=[
                {"product_id": "PROD-AGUA01", "qty": 2.0, "unit_cost": 5.0},
                {"product_id": "PROD-AGUA01", "qty": 3.0, "unit_cost": 4.0},
            ])),
            current_user={"username": "admin_test"},
        ))

        assert db.hotel_products.find_one({"product_id": "PROD-AGUA01"})["quantity_available"] == 10
        assert db.fact_inventory.count_documents({
            "prop_id": 1, "product_id": "PROD-AGUA01", "invoice_ref": created["id"],
        }) == 2
        assert db.ledger_transactions.count_documents({
            "source": "hotel_product_restock",
            "source_id": {"$regex": f"^{created['id']}:line:"},
        }) == 4

    def test_product_backed_approval_rejects_balanced_but_wrong_amount_pair(self, db):
        """Balanced is not enough: AP must equal the received line amount."""
        _seed_product(db)
        created = _dump(create_invoice(
            payload=InvoiceCreate(**_base_payload(product_lines=[
                {"product_id": "PROD-AGUA01", "qty": 2.0, "unit_cost": 5.0},
            ])),
            current_user={"username": "admin_test"},
        ))
        db.ledger_transactions.update_many(
            {"source": "hotel_product_restock", "source_id": f"{created['id']}:line:0"},
            {"$set": {"debit": 99.0, "credit": 99.0}},
        )

        with pytest.raises(HTTPException) as exc_info:
            update_invoice(
                invoice_id=created["id"],
                prop_id=1,
                payload=InvoiceUpdate(status="approved"),
                current_user={"username": "admin_test"},
            )
        assert exc_info.value.status_code == 409

    def test_product_backed_invoice_cannot_change_amount_after_restock(self, db):
        """Inventory receipt and payable snapshot cannot drift independently."""
        _seed_product(db)
        created = _dump(create_invoice(
            payload=InvoiceCreate(**_base_payload(product_lines=[
                {"product_id": "PROD-AGUA01", "qty": 2.0, "unit_cost": 5.0},
            ])),
            current_user={"username": "admin_test"},
        ))

        with pytest.raises(HTTPException) as exc_info:
            update_invoice(
                invoice_id=created["id"],
                prop_id=1,
                payload=InvoiceUpdate(amount=20.0),
                current_user={"username": "admin_test"},
            )
        assert exc_info.value.status_code == 409
        assert db.expense_invoices.find_one({"_id": ObjectId(created["id"])})["amount"] == 10.0

    def test_multiple_product_lines_keep_separate_restock_journals(self, db):
        """Each inventory line has an independent idempotency key."""
        _seed_product(db, product_id="PROD-AGUA01")
        _seed_product(db, product_id="PROD-AGUA02", name="Jugo")
        created = _dump(create_invoice(
            payload=InvoiceCreate(**_base_payload(product_lines=[
                {"product_id": "PROD-AGUA01", "qty": 2.0, "unit_cost": 5.0},
                {"product_id": "PROD-AGUA02", "qty": 3.0, "unit_cost": 4.0},
            ])),
            current_user={"username": "admin_test"},
        ))

        assert db.hotel_products.find_one({"product_id": "PROD-AGUA01"})["quantity_available"] == 7
        assert db.hotel_products.find_one({"product_id": "PROD-AGUA02"})["quantity_available"] == 8
        assert db.ledger_transactions.count_documents({
            "source": "hotel_product_restock",
            "source_id": {"$regex": f"^{created['id']}:line:"},
        }) == 4

        approved = update_invoice(
            invoice_id=created["id"],
            prop_id=1,
            payload=InvoiceUpdate(status="approved"),
            current_user={"username": "admin_test"},
        )
        assert approved.ledger_posting_status == "posted"

        db.ledger_transactions.delete_one({
            "source": "hotel_product_restock",
            "source_id": {"$regex": f"^{created['id']}:line:"},
        })
        with pytest.raises(HTTPException) as exc_info:
            update_invoice(
                invoice_id=created["id"],
                prop_id=1,
                payload=InvoiceUpdate(status="approved"),
                current_user={"username": "admin_test"},
            )
        assert exc_info.value.status_code == 409

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

        detail = _dump(get_invoice(request=_fake_request(), invoice_id=created["id"], prop_id=1))

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
        detail = _dump(get_invoice(request=_fake_request(), invoice_id=created["id"], prop_id=1))
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

        detail = _dump(get_invoice(request=_fake_request(), invoice_id=created["id"], prop_id=1))
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
