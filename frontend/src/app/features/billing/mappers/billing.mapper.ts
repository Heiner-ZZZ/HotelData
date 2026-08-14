import type { BillableServicesDto, InvoiceDashboardDto, InvoiceDetailDto, InvoiceItemDto, InvoicesListDto, LineItemDto, PaymentDashboardDto, PaymentDto, PaymentItemDto, PaymentsListDto, PaymentLinkCandidatesDto, ShiftCandidateDto } from '../models/billing.dto';
import type { BillableServices, InvoiceDashboard, InvoiceDetailViewModel, InvoiceListItem, InvoicesListViewModel, LineItem, PaymentDashboard, PaymentItem, PaymentListItem, PaymentsListViewModel, PaymentLinkCandidates, ShiftCandidate } from '../models/billing.model';

function mapLineItem(dto: LineItemDto): LineItem {
  return {
    itemId: dto.item_id,
    productId: dto.product_id,
    name: dto.name,
    quantity: dto.quantity ?? 0,
    unitPrice: dto.unit_price ?? 0,
    total: dto.total ?? 0,
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
    originalTotal: dto.original_total ?? dto.total,
    recognizedTotal: dto.recognized_total ?? (dto.status === 'cancelled' || dto.status === 'refunded' ? 0 : dto.total),
    netTotal: dto.net_total ?? (dto.status === 'cancelled' || dto.status === 'refunded' ? 0 : dto.total),
    accountingStatus: dto.accounting_status ?? null,
    accountingReversalJournalId: dto.accounting_reversal_journal_id ?? null,
    creditNoteId: dto.credit_note_id ?? null,
    creditNoteNumber: dto.credit_note_number ?? null,
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
    checkInTime: dto.check_in_time || undefined,
    checkOutTime: dto.check_out_time || undefined,
    totalNights: dto.total_nights,
    rooms: dto.rooms,
    roomTypeName: dto.room_type_name,
    roomLabels: dto.room_labels || [],
    payments: (dto.payments || []).map(mapPaymentDto),
    folioId: dto.folio_id ?? null,
    folioNumber: dto.folio_number ?? null,
    ledgerPostingStatus: dto.ledger_posting_status ?? 'pending',
    ledgerPostingError: dto.ledger_posting_error ?? null,
    ledgerReferences: dto.ledger_references ?? [],
  };
}

function mapPaymentDto(item: PaymentDto & { id?: string }): PaymentItem {
  return {
    id: item.id || (item as any)._id,
    bookingId: item.booking_id,
    invoiceId: item.invoice_id,
    refundId: item.refund_id ?? null,
    refundDocumentId: item.refund_document_id ?? null,
    refundDocumentNumber: item.refund_document_number ?? null,
    reconciliationStatus: item.reconciliation_status ?? null,
    reconciliationReason: item.reconciliation_reason ?? null,
    amount: item.amount ?? 0,
    method: item.method,
    status: item.status,
    reference: item.reference,
    paidAt: item.paid_at,
    shiftId: item.shift_id ?? null,
    shiftEmployee: item.shift_employee ?? null,
    shiftOpenedBy: item.shift_opened_by ?? null,
    shiftType: item.shift_type ?? null,
    refundShiftId: item.refund_shift_id ?? null,
    refundShiftEmployee: item.refund_shift_employee ?? null,
  };
}

function mapPaymentItem(item: PaymentItemDto & { id?: string }): PaymentListItem {
  return {
    id: item.id || item._id,
    bookingId: item.booking_id,
    invoiceId: item.invoice_id,
    refundId: item.refund_id ?? null,
    refundDocumentId: item.refund_document_id ?? null,
    refundDocumentNumber: item.refund_document_number ?? null,
    reconciliationStatus: item.reconciliation_status ?? null,
    reconciliationReason: item.reconciliation_reason ?? null,
    amount: item.amount ?? 0,
    method: item.method,
    status: item.status,
    reference: item.reference,
    paidAt: item.paid_at,
    shiftId: item.shift_id ?? null,
    shiftEmployee: item.shift_employee ?? null,
    shiftOpenedBy: item.shift_opened_by ?? null,
    shiftType: item.shift_type ?? null,
    refundShiftId: item.refund_shift_id ?? null,
    refundShiftEmployee: item.refund_shift_employee ?? null,
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
    legacyPendingCount: dto.legacy_pending_count ?? 0,
  };
}

export function mapInvoiceDashboard(dto: InvoiceDashboardDto): InvoiceDashboard {
  return {
    available: dto.available,
    source: dto.source,
    dateFrom: dto.date_from,
    dateTo: dto.date_to,
    propId: dto.prop_id,
    summary: {
      invoiceCount: dto.summary?.invoice_count ?? 0,
      subtotal: dto.summary?.subtotal ?? 0,
      taxes: dto.summary?.taxes ?? 0,
      totalAmount: dto.summary?.total_amount ?? 0,
      paidTotal: dto.summary?.paid_total ?? 0,
      pendingTotal: dto.summary?.pending_total ?? 0,
      cancelledTotal: dto.summary?.cancelled_total ?? 0,
      byStatus: dto.summary?.by_status ?? {},
      byHotel: (dto.summary?.by_hotel ?? []).map(h => ({
        propId: h.prop_id,
        hotelLabel: h.hotel_label,
        invoiceCount: h.invoice_count,
        total: h.total,
      })),
    },
    series: dto.series ?? { labels: [], datasets: [] },
    rows: (dto.rows ?? []).map(row => ({
      date: row.date,
      propId: row.prop_id,
      hotelLabel: row.hotel_label,
      status: row.status,
      invoiceCount: row.invoice_count,
      subtotal: row.subtotal,
      taxes: row.taxes,
      total: row.total,
      paidTotal: row.paid_total,
      pendingTotal: row.pending_total,
      cancelledTotal: row.cancelled_total,
    })),
    total: dto.total ?? 0,
    page: dto.page ?? 1,
    pageSize: dto.page_size ?? 20,
    totalPages: dto.total_pages ?? 1,
    hasNext: dto.has_next ?? false,
    hasPrev: dto.has_prev ?? false,
    message: dto.message,
  };
}

export function mapPaymentDashboard(dto: PaymentDashboardDto): PaymentDashboard {
  return {
    available: dto.available,
    source: dto.source,
    dateFrom: dto.date_from,
    dateTo: dto.date_to,
    propId: dto.prop_id,
    summary: {
      paymentCount: dto.summary?.payment_count ?? 0,
      paidAmount: dto.summary?.paid_amount ?? 0,
      refundedAmount: dto.summary?.refunded_amount ?? 0,
      failedAmount: dto.summary?.failed_amount ?? 0,
      invoicedAmount: dto.summary?.invoiced_amount ?? 0,
      collectedAmount: dto.summary?.collected_amount ?? 0,
      outstandingAmount: dto.summary?.outstanding_amount ?? 0,
      byMethod: (dto.summary?.by_method ?? []).map(m => ({
        method: m.method,
        label: m.label,
        count: m.count,
        amount: m.amount,
      })),
      byStatus: dto.summary?.by_status ?? {},
      byHotel: (dto.summary?.by_hotel ?? []).map(h => ({
        propId: h.prop_id,
        hotelLabel: h.hotel_label,
        paymentCount: h.payment_count,
        collectedAmount: h.collected_amount,
      })),
    },
    series: dto.series ?? { labels: [], datasets: [] },
    rows: (dto.rows ?? []).map(row => ({
      date: row.date,
      propId: row.prop_id,
      hotelLabel: row.hotel_label,
      method: row.method,
      status: row.status,
      paymentCount: row.payment_count,
      paidAmount: row.paid_amount,
      refundedAmount: row.refunded_amount,
      failedAmount: row.failed_amount,
      invoicedAmount: row.invoiced_amount,
      collectedAmount: row.collected_amount,
      outstandingAmount: row.outstanding_amount,
    })),
    total: dto.total ?? 0,
    page: dto.page ?? 1,
    pageSize: dto.page_size ?? 20,
    totalPages: dto.total_pages ?? 1,
    hasNext: dto.has_next ?? false,
    hasPrev: dto.has_prev ?? false,
    message: dto.message,
  };
}

export function mapShiftCandidate(dto: ShiftCandidateDto): ShiftCandidate {
  return {
    id: dto.id,
    propId: dto.prop_id ?? 0,
    status: dto.status,
    shiftType: dto.shift_type ?? null,
    employee: dto.employee ?? null,
    openedBy: dto.opened_by ?? null,
    startTime: dto.start_time ?? null,
    closedAt: dto.closed_at ?? null,
  };
}

export function mapPaymentLinkCandidates(dto: PaymentLinkCandidatesDto): PaymentLinkCandidates {
  return {
    payment: mapPaymentItem(dto.payment),
    shifts: (dto.shifts || []).map(mapShiftCandidate),
  };
}

export function mapBillableServices(dto: BillableServicesDto): BillableServices {
  return {
    categories: (dto.categories || []).map(cat => ({
      category: cat.category,
      items: (cat.items || []).map(item => ({
        label: item.label,
        unitPrice: item.unit_price ?? 0,
      })),
    })),
    chargeable: (dto.chargeable || []).map(item => ({
      label: item.label,
      unitPrice: item.unit_price ?? 0,
    })),
    all_items: (dto.all_items || []).map(item => ({
      label: item.label,
      unitPrice: item.unit_price ?? 0,
    })),
  };
}
