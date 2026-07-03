from __future__ import annotations

from pymongo import ASCENDING, DESCENDING, IndexModel

from src.database.collections import ensure_collection

INVOICES_COLLECTION = "expense_invoices"
CATEGORIES_COLLECTION = "expense_categories"
BUDGET_COLLECTION = "expense_budget"
LEDGER_COLLECTION = "ledger_transactions"

INVOICES_INDEXES = [
    IndexModel([("vendor_name", ASCENDING)], name="idx_inv_vendor"),
    IndexModel([("category", ASCENDING)], name="idx_inv_category"),
    IndexModel([("status", ASCENDING)], name="idx_inv_status"),
    IndexModel([("created_at", DESCENDING)], name="idx_inv_created"),
    IndexModel([("prop_id", ASCENDING)], name="idx_inv_prop"),
    IndexModel([("due_date", ASCENDING)], name="idx_inv_due"),
]

CATEGORIES_INDEXES = [
    IndexModel([("name", ASCENDING)], name="idx_cat_name", unique=True),
]

BUDGET_INDEXES = [
    IndexModel([("department", ASCENDING), ("period", ASCENDING)], name="idx_budget_dept_period", unique=True),
]

LEDGER_INDEXES = [
    IndexModel([("prop_id", ASCENDING)], name="idx_ledger_prop"),
    IndexModel([("tx_date", DESCENDING)], name="idx_ledger_date"),
    IndexModel([("folio_ref", ASCENDING)], name="idx_ledger_folio"),
    IndexModel([("status", ASCENDING)], name="idx_ledger_status"),
    IndexModel([("account_code", ASCENDING)], name="idx_ledger_account"),
]


def ensure_expenses_collections() -> None:
    ensure_collection(INVOICES_COLLECTION, INVOICES_INDEXES)
    ensure_collection(CATEGORIES_COLLECTION, CATEGORIES_INDEXES)
    ensure_collection(BUDGET_COLLECTION, BUDGET_INDEXES)
    ensure_collection(LEDGER_COLLECTION, LEDGER_INDEXES)


def module_status() -> ModuleStatus:
    from src.app.modules.expenses.schemas import ModuleStatus
    return ModuleStatus(
        module="expenses",
        status="active",
        description="Control de gastos, libro mayor, facturas, presupuestos y categorías.",
    )
