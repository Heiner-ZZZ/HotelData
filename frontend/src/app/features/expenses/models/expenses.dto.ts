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
  id: string;
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

export interface InvoiceProductLineDto {
  product_id: string;
  name: string;
  qty: number;
  unit_cost: number;
  line_total: number;
  restocked: boolean;
  /** Live inventory context resolved at read time (null if product deleted). */
  stock_now: number | null;
  cost_now: number | null;
}

export interface InvoiceDetailDto {
  id: string;
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
  product_lines?: InvoiceProductLineDto[];
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
