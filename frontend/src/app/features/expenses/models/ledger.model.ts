export interface LedgerTransaction {
  id: string;
  /** Raw Mongo ObjectId (string form). Optional — present in API responses. */
  _id?: string;
  /** Runtime marker set by `rebuildTreeData` when a journal-entry group is expanded. */
  __isChild?: boolean;
  /** Runtime marker set by `rebuildTreeData` for synthetic journal-entry group rows. */
  __groupRow?: boolean;
  journalEntryId: string;
  entryType: 'auto' | 'manual';
  txDate: string;
  accountCode: string;
  accountName: string;
  description: string;
  debit: number;
  credit: number;
  balance: number;
  costCenter: string;
  folioRef: string;
  bookingId: string;
  propId: number | null;
  guestName: string;
  source: string;
  sourceId: string;
  accountingPeriod: string;
  status: 'audited' | 'pending' | 'discrepancy';
  notes: string;
  createdAt: string;
}

export interface LedgerFolio {
  propId: number;
  folioId: string;
  folioRef: string;
  guestName: string;
  room: string;
  checkIn: string;
  checkOut: string;
  balance: number;
  transactionCount: number;
  bookingId: string;
  status: string;
}

export interface LedgerSummary {
  totalDebits: number;
  totalCredits: number;
  trialBalanceDiff: number;
  isBalanced: boolean;
  transactionCount: number;
  journalEntryCount: number;
  revenueBreakdown: { accountCode: string; total: number }[];
}

export interface TrialBalanceRow {
  accountCode: string;
  accountName: string;
  accountType: string;
  normalBalance: string;
  totalDebits: number;
  totalCredits: number;
  balance: number;
  txCount: number;
  isZeroBalance: boolean;
}

export interface TrialBalance {
  rows: TrialBalanceRow[];
  totals: {
    totalDebits: number;
    totalCredits: number;
    difference: number;
    isBalanced: boolean;
  };
  filters: { propId: number | null; accountingPeriod: string | null };
  accountCount: number;
}

export interface StatementLine {
  accountCode: string;
  accountName: string;
  debits: number;
  credits: number;
  net: number;
}

export interface StatementSection {
  lines: StatementLine[];
  total: number;
}

export interface IncomeStatement {
  period: string | null;
  propId: number;
  revenue: StatementSection;
  discounts: StatementSection;
  netRevenue: number;
  costs: StatementSection;
  netIncome: number;
}

export interface BalanceSheet {
  period: string | null;
  propId: number;
  assets: StatementSection;
  liabilities: StatementSection;
  equity: StatementSection;
  netIncome: number;
  totalLiabilitiesAndEquity: number;
  isBalanced: boolean;
}

export interface ChartAccount {
  accountCode: string;
  accountName: string;
  description: string;
  normalBalance: string;
}

export interface FolioPosting {
  postingId: string;
  type: 'room' | 'charge' | 'discount' | 'payment' | 'adjustment';
  category: string;
  concept: string;
  amount: number;
  quantity: number;
  unitPrice: number;
  referenceId: string;
  referenceType: string;
  postedAt: string;
}

export interface FolioPostingsResponse {
  folioId: string;
  folioRef: string;
  guestName: string;
  postings: FolioPosting[];
}
