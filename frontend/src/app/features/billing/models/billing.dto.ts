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
