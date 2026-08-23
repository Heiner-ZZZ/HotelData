import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, throwError } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapBillableServices, mapInvoiceDashboard, mapInvoiceDetail, mapInvoicesList, mapPaymentsList, mapPaymentDashboard, mapPaymentLinkCandidates } from '../mappers/billing.mapper';
import type { BillableServicesDto, InvoiceDashboardDto, InvoiceDetailDto, InvoiceStatsDto, InvoicesListDto, PaymentDashboardDto, PaymentDto, PaymentsListDto, PaymentItemDto, PaymentLinkCandidatesDto } from '../models/billing.dto';

@Injectable({ providedIn: 'root' })
export class BillingApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getInvoices(page: number, filters?: { prop_id?: number; status?: string; q?: string; date_from?: string; date_to?: string; turno?: string; cajero?: string }) {
    if (!filters?.prop_id || filters.prop_id < 1) {
      return throwError(() => new Error('Selecciona un hotel para consultar Guest AR.'));
    }
    let params = new HttpParams().set('page', String(page));
    if (filters?.prop_id) params = params.set('prop_id', String(filters.prop_id));
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.q) params = params.set('q', filters.q);
    if (filters?.date_from) params = params.set('date_from', filters.date_from);
    if (filters?.date_to) params = params.set('date_to', filters.date_to);
    if (filters?.turno) params = params.set('turno', filters.turno);
    if (filters?.cajero) params = params.set('cajero', filters.cajero);
    return this.http
      .get<InvoicesListDto>(`${this.apiConfig.baseUrl}/billing/invoices`, { params, withCredentials: true })
      .pipe(map(dto => mapInvoicesList(dto)));
  }

  getInvoiceStats(propId: number) {
    if (!propId || propId < 1) {
      return throwError(() => new Error('Selecciona un hotel para consultar Guest AR.'));
    }
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.get<InvoiceStatsDto>(
      `${this.apiConfig.baseUrl}/billing/invoices/stats`,
      { params, withCredentials: true },
    );
  }

  /** Tactical F1.4 dashboard: billed amount per period (ClickHouse). */
  getInvoiceDashboard(params: {
    prop_id?: number;
    date_from?: string;
    date_to?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }) {
    if (!params.prop_id || params.prop_id < 1) {
      return throwError(() => new Error('Selecciona un hotel para consultar Guest AR.'));
    }
    let hp = new HttpParams().set('prop_id', String(params.prop_id));
    if (params.date_from) hp = hp.set('date_from', params.date_from);
    if (params.date_to) hp = hp.set('date_to', params.date_to);
    if (params.status) hp = hp.set('status', params.status);
    if (params.page) hp = hp.set('page', String(params.page));
    if (params.page_size) hp = hp.set('page_size', String(params.page_size));
    return this.http
      .get<InvoiceDashboardDto>(`${this.apiConfig.baseUrl}/billing/analytics/invoices`, { params: hp, withCredentials: true })
      .pipe(map(dto => mapInvoiceDashboard(dto)));
  }

  getInvoiceDetail(invoiceId: string, propId: number) {
    if (!propId || propId < 1) {
      return throwError(() => new Error('Selecciona un hotel para consultar Guest AR.'));
    }
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http
      .get<InvoiceDetailDto>(`${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}`, { params, withCredentials: true })
      .pipe(map(dto => mapInvoiceDetail(dto)));
  }

  cancelInvoice(invoiceId: string, propId: number, reason?: string) {
    const params = new HttpParams().set('prop_id', String(propId));
    const body: Record<string, string> = {};
    if (reason) body['reason'] = reason;
    return this.http.post(`${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}/cancel`, body, { params, withCredentials: true });
  }

  createCreditNote(invoiceId: string, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.post<InvoiceDetailDto>(
      `${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}/credit-note`,
      {},
      { params, withCredentials: true },
    ).pipe(map(dto => mapInvoiceDetail(dto)));
  }

  repairInvoiceSettlement(invoiceId: string, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.post<InvoiceDetailDto>(
      `${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}/repair-settlement`,
      {},
      { params, withCredentials: true },
    ).pipe(map(dto => mapInvoiceDetail(dto)));
  }

  /** Tactical F1.5 dashboard: payments by method + outstanding balance (ClickHouse). */
  getPaymentsDashboard(params: {
    prop_id?: number;
    date_from?: string;
    date_to?: string;
    method?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }) {
    if (!params.prop_id || params.prop_id < 1) {
      return throwError(() => new Error('Selecciona un hotel para consultar Guest AR.'));
    }
    let hp = new HttpParams().set('prop_id', String(params.prop_id));
    if (params.date_from) hp = hp.set('date_from', params.date_from);
    if (params.date_to) hp = hp.set('date_to', params.date_to);
    if (params.method) hp = hp.set('method', params.method);
    if (params.status) hp = hp.set('status', params.status);
    if (params.page) hp = hp.set('page', String(params.page));
    if (params.page_size) hp = hp.set('page_size', String(params.page_size));
    return this.http
      .get<PaymentDashboardDto>(`${this.apiConfig.baseUrl}/billing/analytics/payments`, { params: hp, withCredentials: true })
      .pipe(map(dto => mapPaymentDashboard(dto)));
  }

  getPayments(page: number, filters?: { prop_id?: number; sin_turno?: boolean; turno?: string; cajero?: string }) {
    if (!filters?.prop_id || filters.prop_id < 1) {
      return throwError(() => new Error('Selecciona un hotel para consultar Guest AR.'));
    }
    let params = new HttpParams().set('page', String(page));
    if (filters?.prop_id) params = params.set('prop_id', String(filters.prop_id));
    if (filters?.sin_turno) params = params.set('sin_turno', 'true');
    if (filters?.turno) params = params.set('turno', filters.turno);
    if (filters?.cajero) params = params.set('cajero', filters.cajero);
    return this.http
      .get<PaymentsListDto>(`${this.apiConfig.baseUrl}/billing/payments`, { params, withCredentials: true })
      .pipe(map(dto => mapPaymentsList(dto)));
  }

  /** Shift options for the audit filters (turno), newest first, per hotel.
   *  Degrades to an empty list when the caller lacks ``shifts.read``. */
  getShiftOptions(propId: number, limit = 100) {
    let params = new HttpParams();
    if (propId) params = params.set('prop_id', String(propId));
    params = params.set('limit', String(limit));
    return this.http
      .get<{ items: Array<{ id: string; employee: string | null; shift_type: string | null; start_time: string | null; status: string | null }> }>(
        `${this.apiConfig.baseUrl}/reception/shifts`,
        { params, withCredentials: true },
      )
      .pipe(map((res) => (res.items ?? []).map((s) => ({
        id: s.id,
        label: `${s.shift_type || 'Turno'} · ${s.employee || '—'} · ${(s.start_time ?? '').slice(0, 16).replace('T', ' ')}`,
      }))));
  }

  /** Candidate shifts (of the payment's hotel) for linking a legacy payment. */
  getPaymentLinkCandidates(paymentId: string, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http
      .get<PaymentLinkCandidatesDto>(
        `${this.apiConfig.baseUrl}/billing/payments/${paymentId}/link-candidates`,
        { params, withCredentials: true },
      )
      .pipe(map(dto => mapPaymentLinkCandidates(dto)));
  }

  /** Link a legacy payment (without shift) to the responsible shift. */
  linkPaymentToShift(paymentId: string, shiftId: string, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.post<PaymentItemDto>(
      `${this.apiConfig.baseUrl}/billing/payments/${paymentId}/link-shift`,
      { shift_id: shiftId },
      { params, withCredentials: true },
    );
  }

  /** Client-facing: list invoices for the current user's bookings. */
  getMyInvoices(page: number) {
    const params = new HttpParams().set('page', String(page));
    return this.http
      .get<InvoicesListDto>(`${this.apiConfig.baseUrl}/billing/my-invoices`, { params, withCredentials: true })
      .pipe(map(dto => mapInvoicesList(dto)));
  }

  /** Fetch billable services (amenities) for the invoice charge page. */
  getServices(propId: number, bookingId?: string) {
    let params = new HttpParams().set('prop_id', String(propId));
    if (bookingId) params = params.set('booking_id', bookingId);
    return this.http
      .get<BillableServicesDto>(`${this.apiConfig.baseUrl}/billing/services`, { params, withCredentials: true })
      .pipe(map(dto => mapBillableServices(dto)));
  }

  /** Add a line item to an invoice (only if status='issued'). */
  addLineItem(invoiceId: string, payload: { name: string; quantity?: number; unit_price?: number; category?: string }, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.post<InvoiceDetailDto>(
      `${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}/items`,
      payload,
      { params, withCredentials: true },
    ).pipe(map(dto => mapInvoiceDetail(dto)));
  }

  /** Remove a line item from an invoice (only if status='issued'). Cannot remove room charge. */
  removeLineItem(invoiceId: string, itemId: string, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.delete<InvoiceDetailDto>(
      `${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}/items/${itemId}`,
      { params, withCredentials: true },
    ).pipe(map(dto => mapInvoiceDetail(dto)));
  }

  payInvoice(invoiceId: string, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.post<{ ok: boolean; message: string; payment: Record<string, unknown> }>(
      `${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}/pay`,
      {},
      { params, withCredentials: true },
    );
  }

  /** Register a payment (or a failed/rejected/declined/error attempt). */
  createPayment(payload: { booking_id: string; invoice_id?: string; amount: number; method: string; status: string }, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.post<PaymentDto>(
      `${this.apiConfig.baseUrl}/billing/payments`,
      payload,
      { params, withCredentials: true },
    );
  }

  refundPayment(paymentId: string, propId: number, refundId?: string, reason?: string) {
    const params = new HttpParams().set('prop_id', String(propId));
    const body: Record<string, string> = {};
    if (refundId) body['refund_id'] = refundId;
    if (reason) body['reason'] = reason;
    return this.http.post<PaymentDto>(
      `${this.apiConfig.baseUrl}/billing/payments/${paymentId}/refund`,
      body,
      { params, withCredentials: true },
    );
  }

  /** Client-facing: simulate payment for an invoice. */
  payMyInvoice(invoiceId: string) {
    return this.http.post<{ ok: boolean; message: string; payment: Record<string, unknown> }>(
      `${this.apiConfig.baseUrl}/billing/my-invoices/${invoiceId}/pay`,
      {},
      { withCredentials: true },
    );
  }
}
