export interface InvoicesListViewModel {
  items: InvoiceListItem[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  hasPrev: boolean;
  hasNext: boolean;
}

export interface InvoiceListItem {
  id: string;
  bookingId: string;
  invoiceNumber: string;
  subtotal: number;
  taxes: number;
  total: number;
  status: string;
  issuedAt: string;
  paidAt: string | null;
  guestName?: string;
  hotelLabel?: string;
  totalPaidAmount?: number;
  totalPendingAmount?: number;
}

export interface InvoiceStats {
  issued: { count: number; total: number };
  paid: { count: number; total: number };
  cancelled: { count: number; total: number };
  refunded: { count: number; total: number };
}

export interface LineItem {
  itemId: string;
  productId?: string;
  name: string;
  category?: string;
  quantity: number;
  unitPrice: number;
  total: number;
}

export interface PaymentItem {
  id: string;
  bookingId: string;
  invoiceId: string | null;
  amount: number;
  method: string;
  status: string;
  reference: string | null;
  paidAt: string;
}

export interface InvoiceDetailViewModel {
  id: string;
  bookingId: string;
  invoiceNumber: string;
  propId: number;
  subtotal: number;
  roomSubtotal: number;
  extrasTotal: number;
  taxes: number;
  total: number;
  totalPaidAmount: number;
  totalPendingAmount: number;
  status: string;
  issuedAt: string;
  paidAt: string | null;
  notes: string | null;
  lineItems: LineItem[];
  guestName: string;
  guestEmail: string;
  guestCedula: string;
  hotelLabel: string;
  checkInDate: string;
  checkOutDate: string;
  checkInTime?: string;
  checkOutTime?: string;
  totalNights: number;
  rooms: number;
  roomTypeName: string;
  roomLabels: string[];
  payments: PaymentItem[];
  folioId: string | null;
  folioNumber: string | null;
}

export interface PaymentsListViewModel {
  items: PaymentListItem[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  hasPrev: boolean;
  hasNext: boolean;
}

export interface PaymentListItem {
  id: string;
  bookingId: string;
  invoiceId: string | null;
  amount: number;
  method: string;
  status: string;
  reference: string | null;
  paidAt: string;
}

/** Row of the tactical F1.4 invoice dashboard (day × hotel × status). */
export interface InvoiceDashboardRow {
  date: string;
  propId: number;
  hotelLabel: string;
  status: string;
  invoiceCount: number;
  subtotal: number;
  taxes: number;
  total: number;
  paidTotal: number;
  pendingTotal: number;
  cancelledTotal: number;
}

/** View model for GET /api/billing/analytics/invoices — F1.4 dashboard. */
export interface InvoiceDashboard {
  available: boolean;
  source: string;
  dateFrom: string;
  dateTo: string;
  propId: number | null;
  summary: {
    invoiceCount: number;
    subtotal: number;
    taxes: number;
    totalAmount: number;
    paidTotal: number;
    pendingTotal: number;
    cancelledTotal: number;
    byStatus: Record<string, { count: number; total: number; label: string } | undefined>;
    byHotel: {
      propId: number;
      hotelLabel: string;
      invoiceCount: number;
      total: number;
    }[];
  };
  series: {
    labels: string[];
    datasets: { label: string; data: number[] }[];
  };
  rows: InvoiceDashboardRow[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
  message?: string;
}

/** Row of the tactical F1.5 payments dashboard (day × hotel × method × status). */
export interface PaymentDashboardRow {
  date: string;
  propId: number;
  hotelLabel: string;
  method: string;
  status: string;
  paymentCount: number;
  paidAmount: number;
  refundedAmount: number;
  failedAmount: number;
  invoicedAmount: number;
  collectedAmount: number;
  outstandingAmount: number;
}

/** View model for GET /api/billing/analytics/payments — F1.5 dashboard. */
export interface PaymentDashboard {
  available: boolean;
  source: string;
  dateFrom: string;
  dateTo: string;
  propId: number | null;
  summary: {
    paymentCount: number;
    paidAmount: number;
    refundedAmount: number;
    failedAmount: number;
    invoicedAmount: number;
    collectedAmount: number;
    outstandingAmount: number;
    byMethod: { method: string; label: string; count: number; amount: number }[];
    byStatus: Record<string, { count: number; amount: number; label: string } | undefined>;
    byHotel: { propId: number; hotelLabel: string; paymentCount: number; collectedAmount: number }[];
  };
  series: {
    labels: string[];
    datasets: { label: string; data: number[] }[];
  };
  rows: PaymentDashboardRow[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
  message?: string;
}

/** A single service item from the amenities catalog (billable charges on invoice). */
export interface BillableServiceItem {
  label: string;
  unitPrice: number;
}

/** A category group of billable services. */
export interface BillableServiceCategory {
  category: string;
  items: BillableServiceItem[];
}

/** Response from GET /api/billing/services. */
export interface BillableServices {
  categories: BillableServiceCategory[];
  chargeable: BillableServiceItem[];
  all_items: BillableServiceItem[];
}
