"""Legacy financial routes must never fall back to a cross-hotel query."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.params import Param

from src.app.modules.billing.routes import (
    invoice_stats_api,
    list_invoices_api,
    list_payments_api,
)
from src.app.modules.expenses.routes import (
    expenses_dashboard,
    get_invoice,
    ledger_summary,
    list_active_folios,
    list_budget,
    list_categories,
    list_ledger,
    list_ledger_periods,
    pay_expense_invoice,
    trial_balance,
    update_invoice,
    delete_invoice,
    get_folio_postings,
    register_folio_payment,
    transfer_folio_charges,
)
from src.app.modules.billing.routes import (
    add_line_item_api,
    cancel_invoice_api,
    create_credit_note_api,
    pay_invoice_api,
    refund_payment_api,
    remove_line_item_api,
    repair_invoice_settlement_api,
)
from src.app.modules.expenses.schemas import InvoiceUpdate as ExpenseInvoiceUpdate


def _request() -> object:
    return SimpleNamespace(
        url="http://test/api/expenses/dashboard",
        state=SimpleNamespace(current_user={"username": "scope_test"}),
    )


@pytest.mark.parametrize(
    "handler, kwargs",
    [
        (expenses_dashboard, {"request": _request()}),
        (list_categories, {"request": _request()}),
        (list_budget, {}),
        (list_ledger, {}),
        (list_active_folios, {}),
        (ledger_summary, {}),
        (list_ledger_periods, {}),
        (trial_balance, {}),
        (get_folio_postings, {"folio_id": "folio-1"}),
        (register_folio_payment, {"folio_id": "folio-1", "amount": 1.0}),
        (transfer_folio_charges, {"folio_id": "folio-1", "target_folio_id": "folio-2", "amount": 1.0}),
    ],
)
def test_legacy_financial_reads_reject_missing_hotel_scope(handler, kwargs):
    with pytest.raises(HTTPException) as exc_info:
        handler(**kwargs)

    assert exc_info.value.status_code == 400
    assert "prop_id" in str(exc_info.value.detail)


@pytest.mark.parametrize(
    "handler, kwargs",
    [
        (list_invoices_api, {"request": _request(), "current_user": {"username": "scope_test"}}),
        (list_payments_api, {"request": _request(), "current_user": {"username": "scope_test"}}),
        (invoice_stats_api, {"request": _request(), "current_user": {"username": "scope_test"}}),
    ],
)
def test_legacy_billing_reads_reject_missing_hotel_scope(handler, kwargs):
    with pytest.raises(HTTPException) as exc_info:
        handler(**kwargs)

    assert exc_info.value.status_code == 400
    assert "prop_id" in str(exc_info.value.detail)


@pytest.mark.parametrize(
    "handler, kwargs",
    [
        (get_invoice, {"request": _request(), "invoice_id": "000000000000000000000000"}),
        (pay_expense_invoice, {"invoice_id": "000000000000000000000000"}),
        (update_invoice, {"invoice_id": "000000000000000000000000", "payload": ExpenseInvoiceUpdate(status="rejected")}),
        (delete_invoice, {"invoice_id": "000000000000000000000000"}),
    ],
)
def test_legacy_vendor_ap_mutations_reject_missing_hotel_scope(handler, kwargs):
    with pytest.raises(HTTPException) as exc_info:
        handler(**kwargs)

    assert exc_info.value.status_code == 400
    assert "prop_id" in str(exc_info.value.detail)


@pytest.mark.parametrize(
    "handler, kwargs",
    [
        (add_line_item_api, {"invoice_id": "000000000000000000000000", "payload": {}}),
        (remove_line_item_api, {"invoice_id": "000000000000000000000000", "item_id": "item-1"}),
        (repair_invoice_settlement_api, {"invoice_id": "000000000000000000000000"}),
        (create_credit_note_api, {"invoice_id": "000000000000000000000000"}),
        (cancel_invoice_api, {"invoice_id": "000000000000000000000000"}),
        (pay_invoice_api, {"invoice_id": "000000000000000000000000"}),
        (refund_payment_api, {"payment_id": "000000000000000000000000"}),
    ],
)
def test_legacy_guest_ar_mutations_reject_missing_hotel_scope(handler, kwargs):
    with pytest.raises(HTTPException) as exc_info:
        handler(**kwargs, current_user={"username": "scope_test"})

    assert exc_info.value.status_code == 400
    assert "prop_id" in str(exc_info.value.detail)


def test_legacy_financial_reads_accept_explicit_hotel_scope(db):
    # Calling the route functions directly mirrors the compatibility aliases
    # used by the existing API tests, while proving the Mongo query receives a
    # concrete property scope instead of an unwrapped Query sentinel.
    request = _request()
    assert expenses_dashboard(request=request, prop_id=1).model_dump()["month_total"] == 0
    assert list_categories(request=request, prop_id=1) == []
    assert list_budget(prop_id=1).items == []
    assert list_ledger(prop_id=1).items == []
    assert list_active_folios(prop_id=1).items == []
    assert ledger_summary(prop_id=1).model_dump()["transaction_count"] == 0
    assert list_ledger_periods(prop_id=1) == []
    assert trial_balance(prop_id=1).model_dump()["account_count"] == 0
