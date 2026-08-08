export interface InvoiceListItem {
  id: string;
  vendorName: string;
  category: string;
  description: string;
  amount: number;
  taxAmount: number;
  total: number;
  status: string;
  invoiceDate: string;
  dueDate: string;
  createdAt: string;
}

export interface InvoiceProductLine {
  productId: string;
  name: string;
  qty: number;
  unitCost: number;
  lineTotal: number;
  restocked: boolean;
  /** Live inventory context resolved at read time (null if product deleted). */
  stockNow: number | null;
  costNow: number | null;
}

export interface InvoiceDetail {
  id: string;
  vendorName: string;
  category: string;
  description: string;
  amount: number;
  taxAmount: number;
  total: number;
  status: string;
  invoiceDate: string;
  dueDate: string;
  approvedBy: string | null;
  approvedAt: string | null;
  notes: string;
  propId: number | null;
  productLines: InvoiceProductLine[];
  createdAt: string;
  updatedAt: string;
}

export interface ExpenseDashboard {
  monthTotal: number;
  pendingCount: number;
  pendingValue: number;
  totalBudget: number;
  totalSpent: number;
  budgetExecutionPct: number;
  budgetRemaining: number;
  monthlyBreakdown: { month: string; total: number }[];
  byCategory: { category: string; total: number; count: number }[];
}
