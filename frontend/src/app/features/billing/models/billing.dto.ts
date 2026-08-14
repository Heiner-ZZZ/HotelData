export interface InvoicesListDto {
  items: InvoiceItemDto[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
}

export interface InvoiceItemDto {
  _id: string;
  booking_id: string;
  invoice_number: string;
  subtotal: number;
  taxes: number;
  total: number;
  status: string;
  issued_at: string;
  paid_at: string | null;
  notes: string | null;
  guest_name?: string;
  hotel_label?: string;
  total_paid_amount?: number;
  total_pending_amount?: number;
}

export interface InvoiceStatsDto {
  issued: { count: number; total: number };
  paid: { count: number; total: number };
  cancelled: { count: number; total: number };
  refunded: { count: number; total: number };
}

export interface LineItemDto {
  item_id: string;
  product_id?: string;
  name: string;
  quantity: number;
  unit_price: number;
  total: number;
}

export interface PaymentDto {
  id: string;
  booking_id: string;
  invoice_id: string | null;
  refund_id?: string | null;
  refund_document_id?: string | null;
  refund_document_number?: string | null;
  reconciliation_status?: string | null;
  reconciliation_reason?: string | null;
  amount: number;
  method: string;
  status: string;
  reference: string | null;
  paid_at: string;
  /** Cashier attribution: shift + employee that handled the payment. */
  shift_id?: string | null;
  shift_employee?: string | null;
  shift_opened_by?: string | null;
  shift_type?: string | null;
  /** Refund-side attribution. */
  refund_shift_id?: string | null;
  refund_shift_employee?: string | null;
}

export interface InvoiceDetailDto {
  _id: string;
  booking_id: string;
  invoice_number: string;
  prop_id: number;
  subtotal: number;
  room_subtotal: number;
  extras_total: number;
  taxes: number;
  total: number;
  original_total?: number | null;
  recognized_total?: number | null;
  net_total?: number | null;
  accounting_status?: string | null;
  ledger_posting_status?: 'posted' | 'failed' | string | null;
  ledger_posting_error?: string | null;
  ledger_references?: string[];
  accounting_reversal_journal_id?: string | null;
  credit_note_id?: string | null;
  credit_note_number?: string | null;
  total_paid_amount: number;
  total_pending_amount: number;
  status: string;
  issued_at: string;
  paid_at: string | null;
  notes: string | null;
  line_items: LineItemDto[];
  guest_name: string;
  guest_email: string;
  guest_cedula: string;
  hotel_label: string;
  check_in_date: string;
  check_out_date: string;
  check_in_time?: string;
  check_out_time?: string;
  total_nights: number;
  rooms: number;
  room_type_name: string;
  room_labels: string[];
  payments: PaymentDto[];
  folio_id: string | null;
  folio_number: string | null;
}

export interface PaymentsListDto {
  items: PaymentItemDto[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
  /** Cuántos pagos legacy (sin turno) del hotel están pendientes de vincular. */
  legacy_pending_count?: number;
}

export interface PaymentItemDto {
  _id: string;
  booking_id: string;
  invoice_id: string | null;
  refund_id?: string | null;
  refund_document_id?: string | null;
  refund_document_number?: string | null;
  reconciliation_status?: string | null;
  reconciliation_reason?: string | null;
  amount: number;
  method: string;
  status: string;
  reference: string | null;
  paid_at: string;
  /** Cashier attribution: shift + employee that handled the payment. */
  shift_id?: string | null;
  shift_employee?: string | null;
  shift_opened_by?: string | null;
  shift_type?: string | null;
  /** Refund-side attribution. */
  refund_shift_id?: string | null;
  refund_shift_employee?: string | null;
}

/** Shift candidate for linking a legacy payment (GET /payments/{id}/link-candidates). */
export interface ShiftCandidateDto {
  id: string;
  prop_id: number;
  status: string;
  shift_type: string | null;
  employee: string | null;
  opened_by: string | null;
  start_time: string | null;
  closed_at: string | null;
}

export interface PaymentLinkCandidatesDto {
  payment: PaymentItemDto;
  shifts: ShiftCandidateDto[];
}

/** Row of the tactical F1.4 invoice dashboard (day × hotel × status). */
export interface InvoiceDashboardRowDto {
  date: string;
  prop_id: number;
  hotel_label: string;
  status: string;
  invoice_count: number;
  subtotal: number;
  taxes: number;
  total: number;
  paid_total: number;
  pending_total: number;
  cancelled_total: number;
}

/** Response from GET /api/billing/analytics/invoices — F1.4 dashboard. */
export interface InvoiceDashboardDto {
  available: boolean;
  source: string;
  date_from: string;
  date_to: string;
  prop_id: number | null;
  summary: {
    invoice_count: number;
    subtotal: number;
    taxes: number;
    total_amount: number;
    paid_total: number;
    pending_total: number;
    cancelled_total: number;
    by_status: Record<string, { count: number; total: number; label: string } | undefined>;
    by_hotel: {
      prop_id: number;
      hotel_label: string;
      invoice_count: number;
      total: number;
    }[];
  };
  series: {
    labels: string[];
    datasets: { label: string; data: number[] }[];
  };
  rows: InvoiceDashboardRowDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  message?: string;
}

/** Row of the tactical F1.5 payments dashboard (day × hotel × method × status). */
export interface PaymentDashboardRowDto {
  date: string;
  prop_id: number;
  hotel_label: string;
  method: string;
  status: string;
  payment_count: number;
  paid_amount: number;
  refunded_amount: number;
  failed_amount: number;
  invoiced_amount: number;
  collected_amount: number;
  outstanding_amount: number;
}

/** Response from GET /api/billing/analytics/payments — F1.5 dashboard. */
export interface PaymentDashboardDto {
  available: boolean;
  source: string;
  date_from: string;
  date_to: string;
  prop_id: number | null;
  summary: {
    payment_count: number;
    paid_amount: number;
    refunded_amount: number;
    failed_amount: number;
    invoiced_amount: number;
    collected_amount: number;
    outstanding_amount: number;
    by_method: { method: string; label: string; count: number; amount: number }[];
    by_status: Record<string, { count: number; amount: number; label: string } | undefined>;
    by_hotel: { prop_id: number; hotel_label: string; payment_count: number; collected_amount: number }[];
  };
  series: {
    labels: string[];
    datasets: { label: string; data: number[] }[];
  };
  rows: PaymentDashboardRowDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  message?: string;
}

/** Response from GET /api/billing/services — billable amenities for the invoice page. */
export interface BillableServicesDto {
  categories: {
    category: string;
    items: {
      label: string;
      unit_price: number;
    }[];
  }[];
  chargeable: {
    label: string;
    unit_price: number;
  }[];
  all_items: {
    label: string;
    unit_price: number;
  }[];
}
