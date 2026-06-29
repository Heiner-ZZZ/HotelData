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

export interface LineItem {
  itemId: string;
  productId?: string;
  name: string;
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
  totalNights: number;
  rooms: number;
  roomTypeName: string;
  roomLabels: string[];
  payments: PaymentItem[];
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
