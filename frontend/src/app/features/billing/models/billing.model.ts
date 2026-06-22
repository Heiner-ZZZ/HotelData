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
}

export interface InvoiceDetailViewModel {
  id: string;
  bookingId: string;
  invoiceNumber: string;
  subtotal: number;
  taxes: number;
  total: number;
  status: string;
  issuedAt: string;
  paidAt: string | null;
  notes: string | null;
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
