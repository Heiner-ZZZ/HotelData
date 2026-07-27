from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from src.app.core.types import ObjectIdStr


class ModuleStatus(BaseModel):
    module: str
    status: str
    description: str


# ─── Input DTOs (unchanged) ──────────────────────────────────────────────────


class ExpenseCategoryCreate(BaseModel):
    name: str
    description: str = ""
    budget: float = 0


class InvoiceCreate(BaseModel):
    vendor_name: str
    category: str
    description: str = ""
    amount: float = Field(gt=0)
    tax_amount: float = 0
    invoice_date: str = ""
    due_date: str = ""
    notes: str = ""
    prop_id: int | None = None


class InvoiceUpdate(BaseModel):
    vendor_name: str | None = None
    category: str | None = None
    description: str | None = None
    amount: float | None = Field(default=None, gt=0)
    status: str | None = None  # pending | approved | rejected | paid
    notes: str | None = None


class BudgetCreate(BaseModel):
    department: str
    period: str  # Q1-2026, Q2-2026, etc.
    amount: float = Field(gt=0)
    description: str = ""


class LedgerTransactionCreate(BaseModel):
    tx_date: str
    folio_ref: str
    description: str
    account_code: str
    account_name: str
    debit: float = 0
    credit: float = 0
    status: str = "pending"
    prop_id: int | None = None
    user: str = ""
    notes: str = ""


# ─── Pydantic *Response models (Fase 5/6 API-boundary convention) ────────────
# All class declarations BELOW this banner must be on their OWN line.
# See knowledge.md → "Anti-pattern: from __future__ + Pydantic + response_model"
# for the failure modes this layout prevents.


class ExpenseCategoryResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    name: str
    description: str
    budget: float
    spent: float
    remaining: float
    created_at: str | None = None


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    vendor_name: str | None = None
    category: str | None = None
    category_id: ObjectIdStr | None = Field(default=None, validation_alias="category_id", serialization_alias="category_id")
    description: str | None = None
    amount: float | None = None
    tax_amount: float | None = None
    total: float | None = None
    status: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    notes: str | None = None
    prop_id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class InvoiceListResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    items: list[InvoiceResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 0
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


class BudgetResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    department: str | None = None
    period: str | None = None
    amount: float | None = None
    spent: float | None = None
    remaining: float | None = None
    description: str | None = None
    created_at: str | None = None


class BudgetListResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    items: list[BudgetResponse] = Field(default_factory=list)


class LedgerTransactionResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: ObjectIdStr = Field(validation_alias=AliasChoices("_id", "id"), serialization_alias="id")
    tx_date: str | None = None
    folio_ref: str | None = None
    description: str | None = None
    account_code: str | None = None
    account_name: str | None = None
    debit: float | None = None
    credit: float | None = None
    balance: float | None = None
    status: str | None = None
    # Prop_id may be int (legacy) or ObjectId (post-FK migration). Same
    # transitional pattern as BookingResponse.prop_id — collapses to a
    # single type once the ledger pipeline is fully FK-migrated.
    prop_id: int | ObjectIdStr | None = Field(
        default=None,
        description=(
            "Property FK reference. May be a legacy integer or a "
            "post-migration ObjectId string."
        ),
    )
    user: str | None = None
    notes: str | None = None
    created_at: str | None = None
    accounting_period: str | None = None


class LedgerListResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    items: list[LedgerTransactionResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 0
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False
    total_balance: float | None = None


class LedgerFolioResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    folio_id: str | None = None
    folio_ref: str | None = None
    guest_name: str | None = None
    room: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    balance: float | None = None
    transaction_count: int | None = None
    booking_id: str | None = None
    status: str | None = None


class LedgerFolioListResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    items: list[LedgerFolioResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 0


class FolioPostingsResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    folio_id: str | None = None
    folio_ref: str | None = None
    guest_name: str | None = None
    postings: list[Any] = Field(default_factory=list)


class LedgerSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    total_debits: float | None = None
    total_credits: float | None = None
    trial_balance_diff: float | None = None
    is_balanced: bool | None = None
    transaction_count: int | None = None
    journal_entry_count: int | None = None
    revenue_breakdown: list[Any] = Field(default_factory=list)


class FolioPaymentResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    folio_id: str | None = None
    folio_number: str | None = None
    new_balance: float | None = None
    payment_amount: float | None = None
    method: str | None = None
    invoice_id: str | None = None
    invoice_created: bool | None = None
    payment_reference: str | None = None
    payment_id: str | None = None


class FolioTransferResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source_folio_id: str | None = None
    source_new_balance: float | None = None
    target_folio_id: str | None = None
    target_new_balance: float | None = None
    amount: float | None = None


class TrialBalanceResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    rows: list[Any] = Field(default_factory=list)
    totals: dict[str, Any] | None = None
    filters: dict[str, Any] | None = None
    account_count: int = 0


class IncomeStatementResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    period: str | None = None
    prop_id: int | None = None
    revenue: dict[str, Any] | None = None
    discounts: dict[str, Any] | None = None
    net_revenue: float | None = None
    costs: dict[str, Any] | None = None
    net_income: float | None = None


class BalanceSheetResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    period: str | None = None
    prop_id: int | None = None
    assets: dict[str, Any] | None = None
    liabilities: dict[str, Any] | None = None
    equity: dict[str, Any] | None = None
    net_income: float | None = None
    total_liabilities_and_equity: float | None = None
    is_balanced: bool | None = None


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    month_total: float | None = None
    pending_count: int | None = None
    pending_value: float | None = None
    total_budget: float | None = None
    total_spent: float | None = None
    budget_execution_pct: float | None = None
    budget_remaining: float | None = None
    monthly_breakdown: list[Any] = Field(default_factory=list)
    by_category: list[Any] = Field(default_factory=list)


class ChartOfAccountsResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    items: list[dict[str, Any]] = Field(default_factory=list)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
