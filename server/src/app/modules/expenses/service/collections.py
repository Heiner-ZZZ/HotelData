from __future__ import annotations
from typing import TYPE_CHECKING

from pymongo import ASCENDING, DESCENDING, IndexModel

from src.database.collections import drop_index_safe, ensure_collection

if TYPE_CHECKING:
    from src.app.modules.expenses.schemas import ModuleStatus

INVOICES_COLLECTION = "expense_invoices"
CATEGORIES_COLLECTION = "expense_categories"
BUDGET_COLLECTION = "expense_budget"
LEDGER_COLLECTION = "ledger_transactions"
CHART_OF_ACCOUNTS = "chart_of_accounts"

INVOICES_INDEXES = [
    IndexModel([("vendor_name", ASCENDING)], name="idx_inv_vendor"),
    IndexModel([("category", ASCENDING)], name="idx_inv_category"),
    IndexModel([("category_id", ASCENDING)], name="idx_inv_category_id"),
    IndexModel([("status", ASCENDING)], name="idx_inv_status"),
    IndexModel([("created_at", DESCENDING)], name="idx_inv_created"),
    IndexModel([("prop_id", ASCENDING)], name="idx_inv_prop"),
    IndexModel([("due_date", ASCENDING)], name="idx_inv_due"),
]

CATEGORIES_INDEXES = [
    IndexModel([("name", ASCENDING)], name="idx_cat_name", unique=True),
]

BUDGET_INDEXES = [
    # A hotel may use the same department/period as another hotel. Legacy
    # rows without prop_id remain outside this unique index until explicitly
    # classified; new hotel-scoped budgets are unique per property.
    IndexModel(
        [("prop_id", ASCENDING), ("department", ASCENDING), ("period", ASCENDING)],
        name="idx_budget_prop_dept_period",
        unique=True,
        # Mongo partial indexes do not accept `$ne: null`; all hotel tenant
        # keys are integer prop_id values, so `$type: int` is the safe filter.
        partialFilterExpression={"prop_id": {"$type": "int"}},
    ),
]

LEDGER_INDEXES = [
    IndexModel([("prop_id", ASCENDING)], name="idx_ledger_prop"),
    IndexModel([("tx_date", DESCENDING)], name="idx_ledger_date"),
    IndexModel([("folio_ref", ASCENDING)], name="idx_ledger_folio"),
    IndexModel([("status", ASCENDING)], name="idx_ledger_status"),
    IndexModel([("account_code", ASCENDING)], name="idx_ledger_account"),
    IndexModel([("journal_entry_id", ASCENDING)], name="idx_ledger_journal"),
    # One source event owns exactly one journal pair. This makes retries safe
    # and lets reconciliation distinguish a complete pair from a half-write.
    IndexModel([("source", ASCENDING), ("source_id", ASCENDING), ("account_code", ASCENDING)], name="idx_ledger_source_account", unique=True, partialFilterExpression={"source_id": {"$exists": True, "$ne": ""}}),
]

CHART_INDEXES = [
    IndexModel([("account_code", ASCENDING)], name="idx_chart_code", unique=True),
    IndexModel([("account_type", ASCENDING)], name="idx_chart_type"),
]


def ensure_expenses_collections() -> None:
    # Replace the pre-hotel-scoping unique index. Keeping it would reject the
    # same department/period in a second hotel even though the records are
    # unrelated.
    drop_index_safe(BUDGET_COLLECTION, "idx_budget_dept_period")
    ensure_collection(INVOICES_COLLECTION, INVOICES_INDEXES)
    ensure_collection(CATEGORIES_COLLECTION, CATEGORIES_INDEXES)
    ensure_collection(BUDGET_COLLECTION, BUDGET_INDEXES)
    ensure_collection(LEDGER_COLLECTION, LEDGER_INDEXES)
    ensure_collection(CHART_OF_ACCOUNTS, CHART_INDEXES)


def module_status() -> ModuleStatus:
    from src.app.modules.expenses.schemas import ModuleStatus
    return ModuleStatus(
        module="expenses",
        status="active",
        description="Control de gastos, libro mayor, facturas, presupuestos y categorías.",
    )
