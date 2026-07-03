export interface InvoiceListDto {
  items: InvoiceItemDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface InvoiceItemDto {
  _id: string;
  vendor_name: string;
  category: string;
  description: string;
  amount: number;
  tax_amount: number;
  total: number;
  status: string;
  invoice_date: string;
  due_date: string;
  created_at: string;
}

export interface InvoiceDetailDto {
  _id: string;
  vendor_name: string;
  category: string;
  description: string;
  amount: number;
  tax_amount: number;
  total: number;
  status: string;
  invoice_date: string;
  due_date: string;
  approved_by: string | null;
  approved_at: string | null;
  notes: string;
  prop_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface ExpenseDashboardDto {
  month_total: number;
  pending_count: number;
  pending_value: number;
  total_budget: number;
  total_spent: number;
  budget_execution_pct: number;
  budget_remaining: number;
  monthly_breakdown: { month: string; total: number }[];
  by_category: { category: string; total: number; count: number }[];
}

export interface ExpenseCategoryDto {
  _id: string;
  name: string;
  description: string;
  budget: number;
  spent: number;
  remaining: number;
}
