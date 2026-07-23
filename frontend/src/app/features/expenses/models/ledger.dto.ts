export interface LedgerFolioDto {
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
