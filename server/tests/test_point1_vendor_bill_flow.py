"""Regressions for the VendorBill/AP flow and hotel-scoped expense views."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException

from src.app.modules.expenses.routes import (
    create_budget,
    create_invoice,
    expenses_dashboard,
    list_budget,
    list_categories,
    update_invoice,
)
from src.app.modules.expenses.schemas import BudgetCreate, ExpenseCategoryCreate, InvoiceCreate, InvoiceUpdate


def _request() -> object:
    return SimpleNamespace(
        url="http://test/api/expenses",
        state=SimpleNamespace(current_user={"username": "admin_test"}),
    )


def _invoice_payload(prop_id: int, amount: float, category: str = "Mantenimiento") -> InvoiceCreate:
    return InvoiceCreate(
        vendor_name="Proveedor de prueba",
        category=category,
        amount=amount,
        tax_amount=0,
        prop_id=prop_id,
        invoice_date="2026-08-08",
        due_date="2026-09-08",
    )


def test_pending_vendor_bill_cannot_skip_approval_and_be_marked_paid(db):
    """AP must be posted by approval before a bill can enter the paid state."""
    invoice = create_invoice(
        payload=_invoice_payload(940, 125.0),
        current_user={"username": "admin_test"},
    )

    with pytest.raises(HTTPException) as exc_info:
        update_invoice(
            invoice_id=str(invoice.id),
            prop_id=940,
            payload=InvoiceUpdate(status="paid"),
            current_user={"username": "admin_test"},
        )

    assert exc_info.value.status_code == 409
    stored = db.expense_invoices.find_one({"_id": ObjectId(invoice.id)})
    assert stored["status"] == "pending"
    assert db.ledger_transactions.count_documents({
        "source": "expense_invoice",
        "source_id": str(invoice.id),
    }) == 0


def test_approved_vendor_bill_payment_posts_ap_to_cash_once(db):
    """Paying an approved bill closes AP with one idempotent journal pair."""
    from src.app.modules.expenses.routes import pay_expense_invoice

    invoice = create_invoice(
        payload=_invoice_payload(942, 75.0),
        current_user={"username": "admin_test"},
    )
    update_invoice(
        invoice_id=str(invoice.id),
        prop_id=942,
        payload=InvoiceUpdate(status="approved"),
        current_user={"username": "admin_test"},
    )

    paid = pay_expense_invoice(
        invoice_id=str(invoice.id),
        prop_id=942,
        method="bank_transfer",
        payment_reference="VB-PAY-942-001",
        current_user={"username": "admin_test"},
    )
    retried = pay_expense_invoice(
        invoice_id=str(invoice.id),
        prop_id=942,
        method="bank_transfer",
        payment_reference="VB-PAY-942-001",
        current_user={"username": "admin_test"},
    )

    assert paid.status == "paid"
    assert paid.payment_reference == "VB-PAY-942-001"
    assert retried.status == "paid"
    assert db.ledger_transactions.count_documents({
        "source": "expense_invoice_payment",
        "source_id": str(invoice.id),
    }) == 2
    assert db.expense_invoices.find_one({"_id": ObjectId(invoice.id)})["payment_method"] == "bank_transfer"


def test_expense_dashboard_only_counts_the_requested_hotel(db):
    """Dashboard totals must not leak VendorBills from another hotel."""
    now = datetime.now(timezone.utc)
    db.expense_invoices.insert_many([
        {"prop_id": 940, "status": "pending", "total": 10.0, "created_at": now},
        {"prop_id": 941, "status": "pending", "total": 90.0, "created_at": now},
    ])

    dashboard = expenses_dashboard(request=_request(), prop_id=940)

    assert dashboard.pending_count == 1
    assert dashboard.pending_value == 10.0
    assert dashboard.month_total == 10.0


def test_dashboard_budget_only_counts_the_requested_hotel(db):
    """Budget KPIs must not leak budget allocations from another hotel."""
    now = datetime.now(timezone.utc)
    db.expense_budget.insert_many([
        {"prop_id": 940, "department": "Mantenimiento", "period": "Q3-2026", "amount": 100.0, "created_at": now},
        {"prop_id": 941, "department": "Mantenimiento", "period": "Q3-2026", "amount": 900.0, "created_at": now},
    ])

    dashboard = expenses_dashboard(request=_request(), prop_id=940)

    assert dashboard.total_budget == 100.0


def test_budget_crud_requires_and_preserves_hotel_scope(db):
    """Budget creation and listing must retain the selected hotel's boundary."""
    first = create_budget(BudgetCreate(
        prop_id=940, department="Mantenimiento", period="Q3-2026", amount=100.0,
    ))
    second = create_budget(BudgetCreate(
        prop_id=941, department="Mantenimiento", period="Q3-2026", amount=900.0,
    ))

    assert first.prop_id == 940
    assert second.prop_id == 941
    visible = list_budget(period="Q3-2026", prop_id=940)
    assert [item.prop_id for item in visible.items] == [940]


def test_category_spend_only_counts_the_requested_hotel(db):
    """Category spend must use the same prop_id boundary as the category view."""
    category = db.expense_categories.insert_one({
        "name": "Mantenimiento",
        "description": "",
        "budget": 1000.0,
        "created_at": datetime.now(timezone.utc),
    }).inserted_id
    now = datetime.now(timezone.utc)
    db.expense_invoices.insert_many([
        {
            "prop_id": 940,
            "category": "Mantenimiento",
            "category_id": category,
            "status": "approved",
            "total": 10.0,
            "created_at": now,
        },
        {
            "prop_id": 941,
            "category": "Mantenimiento",
            "category_id": category,
            "status": "approved",
            "total": 90.0,
            "created_at": now,
        },
    ])

    categories = list_categories(request=_request(), prop_id=940)

    maintenance = next(item for item in categories if item.name == "Mantenimiento")
    assert maintenance.spent == 10.0
    assert maintenance.remaining == 990.0
