from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ModuleStatus(BaseModel):
    module: str
    status: str
    description: str


class ExpenseCategoryCreate(BaseModel):
    name: str
    description: str = ""
    budget: float = 0


class ExpenseCategoryResponse(BaseModel):
    id: str = Field(alias="_id")
    name: str
    description: str
    budget: float
    spent: float
    remaining: float
    created_at: str


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


class InvoiceResponse(BaseModel):
    id: str = Field(alias="_id")
    vendor_name: str
    category: str
    description: str
    amount: float
    tax_amount: float
    total: float
    status: str
    invoice_date: str
    due_date: str
    approved_by: str | None
    approved_at: str | None
    notes: str
    prop_id: int | None
    created_at: str
    updated_at: str


class BudgetCreate(BaseModel):
    department: str
    period: str  # Q1-2026, Q2-2026, etc.
    amount: float = Field(gt=0)
    description: str = ""


class BudgetResponse(BaseModel):
    id: str = Field(alias="_id")
    department: str
    period: str
    amount: float
    spent: float
    remaining: float
    created_at: str


# ─── Ledger ───

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


class LedgerTransactionResponse(BaseModel):
    id: str = Field(alias="_id")
    tx_date: str
    folio_ref: str
    description: str
    account_code: str
    account_name: str
    debit: float
    credit: float
    balance: float
    status: str
    prop_id: int | None
    user: str
    notes: str
    created_at: str


class LedgerFolioResponse(BaseModel):
    folio_ref: str
    guest_name: str
    room: str
    check_in: str
    check_out: str
    balance: float
    transaction_count: int


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
