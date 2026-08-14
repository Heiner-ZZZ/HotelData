import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';

export interface FolioPosting {
  postingId: string;
  type: 'room' | 'charge' | 'charge_reversal' | 'refund' | 'discount' | 'payment' | 'adjustment';
  category: string;
  concept: string;
  amount: number;
  quantity: number;
  unitPrice: number;
  referenceId: string;
  referenceType: string;
  postedAt: string;
  /** Cash shift that handled this money movement (front-desk stamped). */
  shiftId: string | null;
  shiftEmployee: string | null;
  shiftOpenedBy: string | null;
  shiftType: string | null;
}

export interface FolioDto {
  id: string;
  folio_number: string;
  booking_id: string;
  prop_id: number;
  guest_name: string;
  guest_email: string;
  room_label: string;
  hotel_label: string;
  check_in_date: string;
  check_out_date: string;
  check_in_time?: string;
  check_out_time?: string;
  status: 'open' | 'closed' | 'settled' | 'written_off' | 'refunded';
  close_reason?: string | null;
  is_expired: boolean;
  has_invoice: boolean;
  total_room: number;
  total_charges: number;
  total_discounts: number;
  total_payments: number;
  total_due: number;
  postings: FolioPostingRaw[];
  posting_count: number;
  created_at: string;
  closed_at: string | null;
  closed_by: string | null;
  reopened_at?: string | null;
  reopened_by?: string | null;
  settlement_type?: string | null;
  settlement_amount?: number | null;
  settlement_reason?: string | null;
  approval_reference?: string | null;
  external_reference?: string | null;
  settled_at?: string | null;
  settled_recorded_at?: string | null;
  settled_by?: string | null;
  settled_by_user_id?: string | null;
  settlement_payment_id?: string | null;
  settlement_payment_ids?: string[];
  settlement_event_id?: string | null;
  settlement_event_ids?: string[];
  settlement_shift_id?: string | null;
  settlement_shift_ids?: string[];
  settlement_invoice_id?: string | null;
  settlement_evidence_type?: string | null;
  settlement_evidence_reference?: string | null;
  invoice_id: string | null;
  /** Shift that opened the folio (check-in cash shift), resolved server-side. */
  created_shift?: {
    shift_id: string;
    shift_type: string;
    shift_label: string;
    employee: string;
    opened_by: string;
    start_time: string;
  } | null;
}

export interface FolioPostingRaw {
  posting_id: string;
  type: string;
  category: string;
  concept: string;
  amount: number;
  quantity: number;
  unit_price: number;
  reference_id: string;
  reference_type: string;
  posted_at: string;
  shift_id?: string | null;
  shift_employee?: string | null;
  shift_opened_by?: string | null;
  shift_type?: string | null;
}

export interface FolioViewModel {
  id: string;
  folioNumber: string;
  bookingId: string;
  propId: number;
  guestName: string;
  guestEmail: string;
  roomLabel: string;
  hotelLabel: string;
  checkInDate: string;
  checkOutDate: string;
  checkInTime?: string;
  checkOutTime?: string;
  status: 'open' | 'closed' | 'settled' | 'written_off' | 'refunded';
  closeReason?: string | null;
  isExpired: boolean;
  hasInvoice: boolean;
  totalRoom: number;
  totalCharges: number;
  totalDiscounts: number;
  totalPayments: number;
  totalDue: number;
  postings: FolioPosting[];
  postingCount: number;
  createdAt: string;
  closedAt: string | null;
  closedBy: string | null;
  reopenedAt: string | null;
  reopenedBy: string | null;
  settlementType: string | null;
  settlementAmount: number | null;
  settlementReason: string | null;
  approvalReference: string | null;
  externalReference: string | null;
  settledAt: string | null;
  settledRecordedAt: string | null;
  settledBy: string | null;
  settledByUserId: string | null;
  settlementPaymentId: string | null;
  settlementPaymentIds: string[];
  settlementEventId: string | null;
  settlementEventIds: string[];
  settlementShiftId: string | null;
  settlementShiftIds: string[];
  settlementInvoiceId: string | null;
  settlementEvidenceType: string | null;
  settlementEvidenceReference: string | null;
  invoiceId: string | null;
  createdShift: {
    shiftId: string;
    shiftType: string;
    shiftLabel: string;
    employee: string;
    openedBy: string;
    startTime: string;
  } | null;
}

export interface FolioPostPayload {
  posting_type: 'charge' | 'discount' | 'payment' | 'adjustment';
  category: string;
  concept: string;
  amount: number;
  quantity?: number;
  reference_id?: string;
  reference_type?: string;
}

export interface FolioClosePayload {
  invoice_id?: string;
  close_reason?: string;
}

export type FolioSettlementType = 'payment' | 'write_off' | 'external_settlement';

export interface FolioSettlementPayload {
  settlement_type: FolioSettlementType;
  idempotency_key: string;
  amount?: number;
  method?: string;
  reason?: string;
  approval_reference?: string;
  external_reference?: string;
}

export type FolioCloseState = 'ready' | 'balance_due' | 'not_open';

export function getFolioCloseState(
  folio: Pick<FolioViewModel, 'status' | 'totalDue'> | null | undefined,
): FolioCloseState {
  if (!folio || folio.status !== 'open') return 'not_open';
  return folio.totalDue > 0.005 ? 'balance_due' : 'ready';
}

export interface FolioCategory {
  id: string;
  label: string;
  icon: string;
}

export function mapFolio(dto: FolioDto): FolioViewModel {
  return {
    id: dto.id,
    folioNumber: dto.folio_number,
    bookingId: dto.booking_id,
    propId: dto.prop_id,
    guestName: dto.guest_name,
    guestEmail: dto.guest_email,
    roomLabel: dto.room_label,
    hotelLabel: dto.hotel_label,
    checkInDate: dto.check_in_date,
    checkOutDate: dto.check_out_date,
    checkInTime: dto.check_in_time || undefined,
    checkOutTime: dto.check_out_time || undefined,
    status: dto.status,
    closeReason: dto.close_reason ?? null,
    isExpired: dto.is_expired ?? false,
    hasInvoice: dto.has_invoice ?? false,
    totalRoom: dto.total_room,
    totalCharges: dto.total_charges,
    totalDiscounts: dto.total_discounts,
    totalPayments: dto.total_payments,
    totalDue: dto.total_due,
    postings: (dto.postings || []).map((p: FolioPostingRaw) => ({
      postingId: p.posting_id,
      type: p.type as FolioPosting['type'],
      category: p.category,
      concept: p.concept,
      amount: p.amount,
      quantity: p.quantity,
      unitPrice: p.unit_price,
      referenceId: p.reference_id,
      referenceType: p.reference_type,
      postedAt: p.posted_at,
      shiftId: p.shift_id ?? null,
      shiftEmployee: p.shift_employee ?? null,
      shiftOpenedBy: p.shift_opened_by ?? null,
      shiftType: p.shift_type ?? null,
    })),
    postingCount: dto.posting_count,
    createdAt: dto.created_at,
    closedAt: dto.closed_at,
    closedBy: dto.closed_by,
    reopenedAt: dto.reopened_at ?? null,
    reopenedBy: dto.reopened_by ?? null,
    settlementType: dto.settlement_type ?? null,
    settlementAmount: dto.settlement_amount ?? null,
    settlementReason: dto.settlement_reason ?? null,
    approvalReference: dto.approval_reference ?? null,
    externalReference: dto.external_reference ?? null,
    settledAt: dto.settled_at ?? null,
    settledRecordedAt: dto.settled_recorded_at ?? null,
    settledBy: dto.settled_by ?? null,
    settledByUserId: dto.settled_by_user_id ?? null,
    settlementPaymentId: dto.settlement_payment_id ?? null,
    settlementPaymentIds: dto.settlement_payment_ids ?? [],
    settlementEventId: dto.settlement_event_id ?? null,
    settlementEventIds: dto.settlement_event_ids ?? [],
    settlementShiftId: dto.settlement_shift_id ?? null,
    settlementShiftIds: dto.settlement_shift_ids ?? [],
    settlementInvoiceId: dto.settlement_invoice_id ?? null,
    settlementEvidenceType: dto.settlement_evidence_type ?? null,
    settlementEvidenceReference: dto.settlement_evidence_reference ?? null,
    invoiceId: dto.invoice_id,
    createdShift: dto.created_shift
      ? {
          shiftId: dto.created_shift.shift_id,
          shiftType: dto.created_shift.shift_type,
          shiftLabel: dto.created_shift.shift_label,
          employee: dto.created_shift.employee,
          openedBy: dto.created_shift.opened_by,
          startTime: dto.created_shift.start_time,
        }
      : null,
  };
}

@Injectable({ providedIn: 'root' })
export class FolioApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/billing/folios';

  /** Get the folio for a booking. */
  getFolio(bookingId: string): Observable<FolioViewModel> {
    return this.http.get<FolioDto>(`${this.base}/${bookingId}`, { withCredentials: true }).pipe(map(mapFolio));
  }

  /** Post a transaction to the guest's folio. */
  postToFolio(bookingId: string, payload: FolioPostPayload): Observable<FolioViewModel> {
    return this.http.post<FolioDto>(`${this.base}/${bookingId}/post`, payload, { withCredentials: true }).pipe(map(mapFolio));
  }

  /** Reopen a closed folio with a collectible balance. */
  reopenFolio(bookingId: string): Observable<FolioViewModel> {
    return this.http.post<FolioDto>(`${this.base}/${bookingId}/reopen`, {}, { withCredentials: true }).pipe(map(mapFolio));
  }

  /** Resolve a positive balance with an explicit payment or approved exception. */
  settleFolio(bookingId: string, payload: FolioSettlementPayload): Observable<FolioViewModel> {
    return this.http.post<FolioDto>(`${this.base}/${bookingId}/settle`, payload, { withCredentials: true }).pipe(map(mapFolio));
  }

  /** Close a folio at check-out. */
  closeFolio(bookingId: string, payload: FolioClosePayload = {}): Observable<FolioViewModel> {
    return this.http.post<FolioDto>(`${this.base}/${bookingId}/close`, payload, { withCredentials: true }).pipe(map(mapFolio));
  }

  /** List folios with optional filters. */
  listFolios(params?: { prop_id?: number; status?: string; page?: number; page_size?: number }): Observable<{ items: FolioDto[]; total: number; page: number; page_size: number; total_pages: number; has_next: boolean; has_prev: boolean }> {
    return this.http.get<{ items: FolioDto[]; total: number; page: number; page_size: number; total_pages: number; has_next: boolean; has_prev: boolean }>(`${this.base}`, { params: params as any });
  }

  /** Get available folio categories. */
  getCategories(): Observable<FolioCategory[]> {
    return this.http.get<FolioCategory[]>(`${this.base}/categories`);
  }
}
