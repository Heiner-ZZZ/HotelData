import type { InvoiceDetailDto, InvoiceItemDto, InvoicesListDto, LineItemDto, PaymentDto, PaymentItemDto, PaymentsListDto } from '../models/billing.dto';
import type { InvoiceDetailViewModel, InvoiceListItem, InvoicesListViewModel, LineItem, PaymentItem, PaymentListItem, PaymentsListViewModel } from '../models/billing.model';

function mapLineItem(dto: LineItemDto): LineItem {
  return {
    itemId: dto.item_id,
    productId: dto.product_id,
    name: dto.name,
    quantity: dto.quantity,
    unitPrice: dto.unit_price,
    total: dto.total,
  };
}

function mapInvoiceItem(item: InvoiceItemDto & { id?: string }): InvoiceListItem {
  return {
    id: item.id || item._id,
    bookingId: item.booking_id,
    invoiceNumber: item.invoice_number,
    subtotal: item.subtotal,
    taxes: item.taxes,
    total: item.total,
    status: item.status,
    issuedAt: item.issued_at,
    paidAt: item.paid_at,
    guestName: item.guest_name,
    hotelLabel: item.hotel_label,
    totalPaidAmount: item.total_paid_amount,
    totalPendingAmount: item.total_pending_amount,
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

export function mapInvoiceDetail(dto: InvoiceDetailDto & { id?: string }): InvoiceDetailViewModel {
  return {
    id: dto.id || dto._id,
    bookingId: dto.booking_id,
    invoiceNumber: dto.invoice_number,
    propId: dto.prop_id,
    subtotal: dto.subtotal,
    roomSubtotal: dto.room_subtotal,
    extrasTotal: dto.extras_total,
    taxes: dto.taxes,
    total: dto.total,
    totalPaidAmount: dto.total_paid_amount ?? 0,
    totalPendingAmount: dto.total_pending_amount ?? 0,
    status: dto.status,
    issuedAt: dto.issued_at,
    paidAt: dto.paid_at,
    notes: dto.notes,
    lineItems: (dto.line_items || []).map(mapLineItem),
    guestName: dto.guest_name,
    guestEmail: dto.guest_email,
    guestCedula: dto.guest_cedula,
    hotelLabel: dto.hotel_label,
    checkInDate: dto.check_in_date,
    checkOutDate: dto.check_out_date,
    totalNights: dto.total_nights,
    rooms: dto.rooms,
    roomTypeName: dto.room_type_name,
    roomLabels: dto.room_labels || [],
    payments: (dto.payments || []).map(mapPaymentDto),
    folioId: dto.folio_id ?? null,
    folioNumber: dto.folio_number ?? null,
  };
}

function mapPaymentDto(item: PaymentDto & { id?: string }): PaymentItem {
  return {
    id: item.id || (item as any)._id,
    bookingId: item.booking_id,
    invoiceId: item.invoice_id,
    amount: item.amount,
    method: item.method,
    status: item.status,
    reference: item.reference,
    paidAt: item.paid_at,
  };
}

function mapPaymentItem(item: PaymentItemDto & { id?: string }): PaymentListItem {
  return {
    id: item.id || item._id,
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
