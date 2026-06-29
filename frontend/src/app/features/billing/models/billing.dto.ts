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
  amount: number;
  method: string;
  status: string;
  reference: string | null;
  paid_at: string;
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
}

export interface PaymentItemDto {
  _id: string;
  booking_id: string;
  invoice_id: string | null;
  amount: number;
  method: string;
  status: string;
  reference: string | null;
  paid_at: string;
}
