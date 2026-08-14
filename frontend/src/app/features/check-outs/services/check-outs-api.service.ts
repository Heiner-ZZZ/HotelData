import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

export interface DateHistoryEntry {
  date: string;
  count: number;
  prop_id?: number;
  hotel_label?: string;
}

export interface BookingCharge {
  id?: string;
  concept: string;
  amount: number;
  quantity: number;
  total: number;
  category: string;
  note: string;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class CheckOutsApiService {
  private readonly http = inject(HttpClient);

  getCheckOutDates(propId?: number) {
    let params = new HttpParams();
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http.get<DateHistoryEntry[]>('/management/check-outs/dates', { params });
  }

  /** Fetch additional charges (consumptions) for a booking before checkout. */
  getBookingCharges(bookingId: string) {
    const params = new HttpParams().set('booking_id', bookingId);
    return this.http.get<{
      items: BookingCharge[];
      total: number;
      page: number;
      page_size: number;
      total_pages: number;
      has_next: boolean;
      has_prev: boolean;
    }>('/housekeeping/charges', { params });
  }

  /** Create an additional charge for a booking before checkout. */
  createCharge(bookingId: string, propId: number, concept: string, amount: number, quantity: number, note = '', category = '') {
    return this.http.post<BookingCharge>(
      '/housekeeping/charges',
      { booking_id: bookingId, prop_id: propId, concept, amount, quantity, note, category },
    );
  }

  /** Delete an additional charge by its ID. */
  deleteCharge(chargeId: string) {
    return this.http.delete<{ ok: boolean; deleted_id: string; booking_id: string }>(
      `/housekeeping/charges/${chargeId}`,
    );
  }

  completeCheckOut(bookingId: string) {
    return this.http.post(`/management/check-outs/${bookingId}/complete`, {});
  }

  /** ═══ Check-Out Detail Page ═══ */

  getCheckOutDetail(bookingId: string) {
    return this.http.get<CheckOutDetailDto>(
      `/management/check-outs/${bookingId}/detail`,
    );
  }

  saveCheckOutDetail(bookingId: string, payload: Partial<CheckOutDetailSavePayload>) {
    return this.http.patch<{ booking_id: string; updated: boolean; fields_updated: string[] }>(
      `/management/check-outs/${bookingId}/detail`,
      payload,
    );
  }

  completeCheckOutWithDetail(bookingId: string, payload: Partial<CheckOutDetailSavePayload> & { split_invoice?: boolean }) {
    return this.http.post<{ booking_id: string; stay_status: string }>(
      `/management/check-outs/${bookingId}/complete`,
      payload,
    );
  }

  /** Emit (generate) an invoice for a booking. */
  emitInvoice(bookingId: string, propId: number, subtotal: number, taxes: number) {
    return this.http.post<{ id: string; invoice_number: string; status: string; total: number }>(
      '/billing/invoices',
      { booking_id: bookingId, prop_id: propId, subtotal, taxes, notes: '' },
    );
  }

  /** Send an existing invoice to the guest by email. */
  sendInvoiceEmail(invoiceId: string) {
    return this.http.post<{ ok: boolean; message: string }>(
      `/billing/invoices/${invoiceId}/email`,
      {},
    );
  }
}

export interface CheckOutInvoiceDto {
  id: string;
  invoice_number: string;
  subtotal: number;
  room_subtotal: number;
  extras_total: number;
  taxes: number;
  total: number;
  status: string;
  issued_at: string;
  paid_at: string | null;
  notes: string | null;
  line_items: {
    type?: string;
    name?: string;
    concept?: string;
    amount?: number;
    quantity?: number;
    total?: number;
    created_at?: string;
  }[];
}

export interface CheckOutDetailDto {
  booking_id: string;
  prop_id: number;
  hotel_label: string;
  folio: string | null;
  guest_name: string;
  guest_email: string;
  guest_phone: string;
  cedula: string;
  check_in_date: string;
  check_in_date_actual: string | null;
  check_in_time_actual: string | null;
  check_in_by: string | null;
  check_out_date: string;
  total_price: number | null;
  currency: string;
  total_nights: number;
  rooms: number;
  room_type_name: string;
  assigned_rooms: {
    hotel_room_id: string;
    room_number: string;
    room_label: string;
    floor: string;
    room_status: string;
  }[];
  status: string;
  stay_status: string;
  payment_method: string;
  booking_source: string;
  total_charges: number;
  deposit_received: boolean;
  payment_pending: boolean;
  invoice: CheckOutInvoiceDto | null;
  charges: BookingCharge[];
  charges_total: number;
  charges_by_category: Record<string, BookingCharge[]>;
  category_totals: Record<string, number>;
  check_out_room_inspected: boolean;
  check_out_keys_returned: boolean;
  check_out_damages_found: boolean;
  check_out_late_checkout_fee: number;
  check_out_discount: number;
  check_out_discount_reason: string;
  check_out_payment_method: string;
  check_out_payment_ref: string;
  check_out_observations: string;
  check_out_date_actual: string | null;
  check_out_time_actual: string | null;
  check_out_by: string | null;
  /** Cash shift that handled the check-out (FK to reception_shifts). */
  check_out_shift_id: string | null;
  /** Responsible cashier + shift label of the check-out, or null. */
  check_out_shift: {
    shift_type: string;
    shift_label: string;
    employee: string;
    opened_by: string;
    start_time: string;
  } | null;
}

export interface CheckOutDetailSavePayload {
  check_out_room_inspected?: boolean;
  check_out_keys_returned?: boolean;
  check_out_damages_found?: boolean;
  check_out_late_checkout_fee?: number;
  check_out_discount?: number;
  check_out_discount_reason?: string;
  check_out_payment_method?: string;
  check_out_payment_ref?: string;
  check_out_observations?: string;
  split_invoice?: boolean;
}
