export interface LedgerTransaction {
  id: string;
  txDate: string;
  folioRef: string;
  description: string;
  accountCode: string;
  accountName: string;
  debit: number;
  credit: number;
  balance: number;
  status: 'audited' | 'pending' | 'discrepancy';
  propId: number | null;
  user: string;
  notes: string;
  createdAt: string;
}

export interface LedgerFolio {
  folioRef: string;
  guestName: string;
  room: string;
  checkIn: string;
  checkOut: string;
  balance: number;
  transactionCount: number;
}

export interface LedgerSummary {
  totalDebits: number;
  totalCredits: number;
  netBalance: number;
  transactionCount: number;
  pendingCount: number;
  auditedCount: number;
  discrepancyCount: number;
}

export interface LedgerListResponse {
  items: LedgerTransaction[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}
