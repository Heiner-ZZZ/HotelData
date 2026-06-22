import type { InvoiceDetailDto, InvoiceItemDto, InvoicesListDto, PaymentItemDto, PaymentsListDto } from '../models/billing.dto';
import type { InvoiceDetailViewModel, InvoiceListItem, InvoicesListViewModel, PaymentListItem, PaymentsListViewModel } from '../models/billing.model';

function mapInvoiceItem(item: InvoiceItemDto): InvoiceListItem {
  return {
    id: item._id,
    bookingId: item.booking_id,
    invoiceNumber: item.invoice_number,
    subtotal: item.subtotal,
    taxes: item.taxes,
    total: item.total,
    status: item.status,
    issuedAt: item.issued_at,
    paidAt: item.paid_at,
  };
}

export function mapInvoicesList(dto: InvoicesListDto): InvoicesListViewModel {
  return {
    items: dto.items.map(mapInvoiceItem),
    page: dto.page,
    pageSize: dto.page_size,
    total: dto.total,
    totalPages: dto.total_pages,
    hasPrev: dto.has_prev,
    hasNext: dto.has_next,
  };
}

export function mapInvoiceDetail(dto: InvoiceDetailDto): InvoiceDetailViewModel {
  return {
    id: dto._id,
    bookingId: dto.booking_id,
    invoiceNumber: dto.invoice_number,
    subtotal: dto.subtotal,
    taxes: dto.taxes,
    total: dto.total,
    status: dto.status,
    issuedAt: dto.issued_at,
    paidAt: dto.paid_at,
    notes: dto.notes,
  };
}

function mapPaymentItem(item: PaymentItemDto): PaymentListItem {
  return {
    id: item._id,
    bookingId: item.booking_id,
    invoiceId: item.invoice_id,
    amount: item.amount,
    method: item.method,
    status: item.status,
    reference: item.reference,
    paidAt: item.paid_at,
  };
}

export function mapPaymentsList(dto: PaymentsListDto): PaymentsListViewModel {
  return {
    items: dto.items.map(mapPaymentItem),
    page: dto.page,
    pageSize: dto.page_size,
    total: dto.total,
    totalPages: dto.total_pages,
    hasPrev: dto.has_prev,
    hasNext: dto.has_next,
  };
}
