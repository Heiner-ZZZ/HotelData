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

export interface InvoiceDetailDto {
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
