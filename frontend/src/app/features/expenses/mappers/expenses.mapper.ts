import type { ExpenseDashboardDto, InvoiceDetailDto, InvoiceItemDto, InvoiceListDto } from '../models/expenses.dto';
import type { ExpenseDashboard, InvoiceDetail, InvoiceListItem } from '../models/expenses.model';

function mapInvoiceItem(dto: InvoiceItemDto): InvoiceListItem {
  return {
    id: dto._id,
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
    id: dto._id,
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
