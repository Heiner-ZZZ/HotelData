export interface LedgerFolioDto {
  prop_id?: number;
  folio_id: string;
  folio_ref: string;
  guest_name: string;
  room: string;
  check_in: string;
  check_out: string;
  balance: number;
  transaction_count: number;
  booking_id: string;
  status: string;
}

export interface LedgerFoliosDto {
  items: LedgerFolioDto[];
  page: number;
  page_size: number;
  total: number;
}

export interface LedgerSummaryDto {
  total_debits: number;
  total_credits: number;
  trial_balance_diff: number;
  is_balanced: boolean;
  transaction_count: number;
  journal_entry_count: number;
  revenue_breakdown: { account_code: string; total: number }[];
}

export interface TrialBalanceRowDto {
  account_code: string;
  account_name: string;
  account_type: string;
  normal_balance: string;
  total_debits: number;
  total_credits: number;
  balance: number;
  tx_count: number;
  is_zero_balance: boolean;
}

export interface TrialBalanceDto {
  rows: TrialBalanceRowDto[];
  totals: {
    total_debits: number;
    total_credits: number;
    difference: number;
    is_balanced: boolean;
  };
  filters: { prop_id: number | null; accounting_period: string | null };
  account_count: number;
}

export interface StatementLineDto {
  account_code: string;
  account_name: string;
  debits: number;
  credits: number;
  net: number;
}

export interface StatementSectionDto {
  lines: StatementLineDto[];
  total: number;
}

export interface IncomeStatementDto {
  period: string | null;
  prop_id: number;
  revenue: StatementSectionDto;
  discounts: StatementSectionDto;
  net_revenue: number;
  costs: StatementSectionDto;
  net_income: number;
}

export interface BalanceSheetDto {
  period: string | null;
  prop_id: number;
  assets: StatementSectionDto;
  liabilities: StatementSectionDto;
  equity: StatementSectionDto;
  net_income: number;
  total_liabilities_and_equity: number;
  is_balanced: boolean;
}

export interface FolioPostingDto {
  posting_id: string;
  type: string;
  category: string;
  concept: string;
  amount: number;
  quantity: number;
  unit_price: number;
  reference_id: string;
  reference_type: string;
  posted_at: string;
  /** Cashier attribution stamped on money postings (optional). */
  shift_id?: string | null;
  shift_employee?: string | null;
  shift_opened_by?: string | null;
  shift_type?: string | null;
}

export interface FolioPostingsDto {
  folio_id: string;
  folio_ref: string;
  guest_name: string;
  postings: FolioPostingDto[];
}

export interface ChartAccountDto {
  account_code: string;
  account_name: string;
  account_type: string;
  normal_balance: string;
  description: string;
}

/**
 * Wire DTO for an individual ledger transaction row. Backend emits snake_case;
 * `mapLedgerTransaction` in `expenses.mapper.ts` converts to the camelCase
 * `LedgerTransaction` model. Required by the page component's
 * `transactionsResource` httpResource generic, which previously was typed as
 * `LedgerTransaction[]` directly — a lie that let snake_case keys leak into
 * the camelCase-typed rowData signal and caused the synthetic group-row
 * collapse (all rows shared `journalEntryId === undefined`, bucketed under
 * the empty-string key, producing exactly one row in AG Grid).
 */
export interface LedgerTransactionDto {
  id?: string;
  _id?: string;
  tx_date: string;
  journal_entry_id: string;
  entry_type: 'auto' | 'manual';
  account_code: string;
  account_name: string;
  description: string;
  debit: number;
  credit: number;
  balance: number;
  cost_center: string;
  folio_ref: string;
  booking_id: string;
  prop_id: number | null;
  guest_name: string;
  source: string;
  source_id: string;
  accounting_period: string;
  status: 'audited' | 'pending' | 'discrepancy';
  notes: string;
  created_at: string;
}

/** Wire envelope for the `/transactions` list endpoint. */
export interface LedgerTransactionsDto {
  items: LedgerTransactionDto[];
  page: number;
  page_size: number;
  total: number;
}
