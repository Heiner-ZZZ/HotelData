import type { ExpenseDashboardDto, InvoiceDetailDto, InvoiceItemDto, InvoiceListDto } from '../models/expenses.dto';
import type { LedgerFolioDto, LedgerFoliosDto, LedgerSummaryDto, TrialBalanceDto, TrialBalanceRowDto, StatementLineDto, IncomeStatementDto, BalanceSheetDto, ChartAccountDto, FolioPostingDto, FolioPostingsDto, LedgerTransactionDto, LedgerTransactionsDto } from '../models/ledger.dto';
import type { ExpenseDashboard, InvoiceDetail, InvoiceListItem } from '../models/expenses.model';
import type { LedgerFolio, LedgerSummary, TrialBalance, TrialBalanceRow, StatementLine, IncomeStatement, BalanceSheet, ChartAccount, FolioPosting, FolioPostingsResponse, LedgerTransaction } from '../models/ledger.model';

function mapInvoiceItem(dto: InvoiceItemDto): InvoiceListItem {
  return {
    id: dto.id,
    vendorName: dto.vendor_name,
    category: dto.category,
    description: dto.description,
    amount: dto.amount,
    taxAmount: dto.tax_amount,
    total: dto.total,
    status: dto.status,
    invoiceDate: dto.invoice_date,
    dueDate: dto.due_date,
    createdAt: dto.created_at,
  };
}

export function mapInvoiceList(dto: InvoiceListDto) {
  return {
    items: dto.items.map(mapInvoiceItem),
    total: dto.total,
    page: dto.page,
    pageSize: dto.page_size,
    totalPages: dto.total_pages,
    hasNext: dto.has_next,
    hasPrev: dto.has_prev,
  };
}

export function mapInvoiceDetail(dto: InvoiceDetailDto): InvoiceDetail {
  return {
    id: dto.id,
    vendorName: dto.vendor_name,
    category: dto.category,
    description: dto.description,
    amount: dto.amount,
    taxAmount: dto.tax_amount,
    total: dto.total,
    status: dto.status,
    invoiceDate: dto.invoice_date,
    dueDate: dto.due_date,
    approvedBy: dto.approved_by,
    approvedAt: dto.approved_at,
    notes: dto.notes,
    propId: dto.prop_id,
    productLines: (dto.product_lines ?? []).map((l) => ({
      productId: l.product_id,
      name: l.name ?? l.product_id,
      qty: l.qty,
      unitCost: l.unit_cost,
      lineTotal: l.line_total,
      restocked: l.restocked !== false,
      stockNow: l.stock_now ?? null,
      costNow: l.cost_now ?? null,
      // KEEP IN SYNC with the mirror mapping in invoice-detail-page.ts `inv()`.
    })),
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export function mapExpenseDashboard(dto: ExpenseDashboardDto): ExpenseDashboard {
  return {
    monthTotal: dto.month_total,
    pendingCount: dto.pending_count,
    pendingValue: dto.pending_value,
    totalBudget: dto.total_budget,
    totalSpent: dto.total_spent,
    budgetExecutionPct: dto.budget_execution_pct,
    budgetRemaining: dto.budget_remaining,
    monthlyBreakdown: dto.monthly_breakdown || [],
    byCategory: dto.by_category || [],
  };
}

// ─── Ledger mappers ───

export function mapLedgerFolios(dto: LedgerFoliosDto) {
  return {
    items: (dto.items || []).map((f: LedgerFolioDto): LedgerFolio => ({
      propId: f.prop_id ?? 0,
      folioId: f.folio_id,
      folioRef: f.folio_ref,
      guestName: f.guest_name,
      room: f.room,
      checkIn: f.check_in,
      checkOut: f.check_out,
      balance: f.balance,
      transactionCount: f.transaction_count,
      bookingId: f.booking_id,
      status: f.status,
    })),
    page: dto.page,
    pageSize: dto.page_size,
    total: dto.total,
  };
}

export function mapLedgerSummary(dto: LedgerSummaryDto): LedgerSummary {
  return {
    totalDebits: dto.total_debits,
    totalCredits: dto.total_credits,
    trialBalanceDiff: dto.trial_balance_diff,
    isBalanced: dto.is_balanced,
    transactionCount: dto.transaction_count,
    journalEntryCount: dto.journal_entry_count,
    revenueBreakdown: (dto.revenue_breakdown || []).map(r => ({
      accountCode: r.account_code,
      total: r.total,
    })),
  };
}

function mapStatementLine(dto: StatementLineDto): StatementLine {
  return {
    accountCode: dto.account_code,
    accountName: dto.account_name,
    debits: dto.debits,
    credits: dto.credits,
    net: dto.net,
  };
}

export function mapIncomeStatement(dto: IncomeStatementDto): IncomeStatement {
  return {
    period: dto.period,
    propId: dto.prop_id,
    revenue: {
      lines: (dto.revenue?.lines || []).map(mapStatementLine),
      total: dto.revenue?.total ?? 0,
    },
    discounts: {
      lines: (dto.discounts?.lines || []).map(mapStatementLine),
      total: dto.discounts?.total ?? 0,
    },
    netRevenue: dto.net_revenue,
    costs: {
      lines: (dto.costs?.lines || []).map(mapStatementLine),
      total: dto.costs?.total ?? 0,
    },
    netIncome: dto.net_income,
  };
}

export function mapBalanceSheet(dto: BalanceSheetDto): BalanceSheet {
  return {
    period: dto.period,
    propId: dto.prop_id,
    assets: {
      lines: (dto.assets?.lines || []).map(mapStatementLine),
      total: dto.assets?.total ?? 0,
    },
    liabilities: {
      lines: (dto.liabilities?.lines || []).map(mapStatementLine),
      total: dto.liabilities?.total ?? 0,
    },
    equity: {
      lines: (dto.equity?.lines || []).map(mapStatementLine),
      total: dto.equity?.total ?? 0,
    },
    netIncome: dto.net_income,
    totalLiabilitiesAndEquity: dto.total_liabilities_and_equity,
    isBalanced: dto.is_balanced,
  };
}

export function mapChartAccounts(dtos: ChartAccountDto[]): ChartAccount[] {
  return dtos.map(d => ({
    accountCode: d.account_code,
    accountName: d.account_name,
    description: d.description || '',
    normalBalance: d.normal_balance,
  }));
}

export function mapFolioPostings(dto: FolioPostingsDto): FolioPostingsResponse {
  return {
    folioId: dto.folio_id,
    folioRef: dto.folio_ref,
    guestName: dto.guest_name,
    postings: (dto.postings || []).map((p: FolioPostingDto): FolioPosting => ({
      postingId: p.posting_id,
      type: p.type as FolioPosting['type'],
      category: p.category,
      concept: p.concept,
      amount: p.amount,
      quantity: p.quantity,
      unitPrice: p.unit_price,
      referenceId: p.reference_id,
      referenceType: p.reference_type,
      postedAt: p.posted_at,
    })),
  };
}

export function mapTrialBalance(dto: TrialBalanceDto): TrialBalance {
  return {
    rows: (dto.rows || []).map((r: TrialBalanceRowDto): TrialBalanceRow => ({
      accountCode: r.account_code,
      accountName: r.account_name,
      accountType: r.account_type,
      normalBalance: r.normal_balance,
      totalDebits: r.total_debits,
      totalCredits: r.total_credits,
      balance: r.balance,
      txCount: r.tx_count,
      isZeroBalance: r.is_zero_balance,
    })),
    totals: {
      totalDebits: dto.totals.total_debits,
      totalCredits: dto.totals.total_credits,
      difference: dto.totals.difference,
      isBalanced: dto.totals.is_balanced,
    },
    filters: {
      propId: dto.filters.prop_id,
      accountingPeriod: dto.filters.accounting_period,
    },
    accountCount: dto.account_count,
  };
}

/**
 * Convert a single wire-transaction DTO to the camelCase LedgerTransaction model.
 * Used by `transactionsResource` in `ledger-page.ts` because httpResource
 * bypasses the mapper pipeline that HttpClient.pipe(map(...)) provides.
 *
 * Defaults `id` from `_id` when the server doesn't supply a stable id, and
 * `propId` to `null` when missing so the tree-builder can rely on the field.
 * Number fields default to 0 to keep AG Grid valueFormatters from crashing
 * on wire-shape inequalities (the template also wraps with `_num`).
 */
export function mapLedgerTransaction(dto: LedgerTransactionDto): LedgerTransaction {
  return {
    id: dto.id ?? dto._id ?? '',
    _id: dto._id,
    journalEntryId: dto.journal_entry_id,
    entryType: dto.entry_type,
    txDate: dto.tx_date,
    accountCode: dto.account_code,
    accountName: dto.account_name ?? '',
    description: dto.description ?? '',
    debit: dto.debit ?? 0,
    credit: dto.credit ?? 0,
    balance: dto.balance ?? 0,
    costCenter: dto.cost_center ?? '',
    folioRef: dto.folio_ref ?? '',
    bookingId: dto.booking_id ?? '',
    propId: dto.prop_id ?? null,
    guestName: dto.guest_name ?? '',
    source: dto.source ?? '',
    sourceId: dto.source_id ?? '',
    accountingPeriod: dto.accounting_period ?? '',
    status: dto.status ?? 'pending',
    notes: dto.notes ?? '',
    createdAt: dto.created_at ?? '',
  };
}

/** Envelope mapper: maps the full /transactions response. */
export function mapLedgerTransactions(dto: LedgerTransactionsDto): LedgerTransaction[] {
  return (dto?.items || []).map(mapLedgerTransaction);
}
