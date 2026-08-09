import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, throwError } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapBillableServices, mapInvoiceDashboard, mapInvoiceDetail, mapInvoicesList, mapPaymentsList, mapPaymentDashboard } from '../mappers/billing.mapper';
import type { BillableServicesDto, InvoiceDashboardDto, InvoiceDetailDto, InvoiceStatsDto, InvoicesListDto, PaymentDashboardDto, PaymentDto, PaymentsListDto } from '../models/billing.dto';

@Injectable({ providedIn: 'root' })
export class BillingApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getInvoices(page: number, filters?: { prop_id?: number; status?: string; q?: string; date_from?: string; date_to?: string }) {
    if (!filters?.prop_id || filters.prop_id < 1) {
      return throwError(() => new Error('Selecciona un hotel para consultar Guest AR.'));
    }
    let params = new HttpParams().set('page', String(page));
    if (filters?.prop_id) params = params.set('prop_id', String(filters.prop_id));
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.q) params = params.set('q', filters.q);
    if (filters?.date_from) params = params.set('date_from', filters.date_from);
    if (filters?.date_to) params = params.set('date_to', filters.date_to);
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

  cancelInvoice(invoiceId: string, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.post(`${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}/cancel`, {}, { params, withCredentials: true });
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

  getPayments(page: number, filters?: { prop_id?: number }) {
    if (!filters?.prop_id || filters.prop_id < 1) {
      return throwError(() => new Error('Selecciona un hotel para consultar Guest AR.'));
    }
    let params = new HttpParams().set('page', String(page));
    if (filters?.prop_id) params = params.set('prop_id', String(filters.prop_id));
    return this.http
      .get<PaymentsListDto>(`${this.apiConfig.baseUrl}/billing/payments`, { params, withCredentials: true })
      .pipe(map(dto => mapPaymentsList(dto)));
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
  createPayment(payload: { booking_id: string; invoice_id?: string; amount: number; method: string; status: string }) {
    return this.http.post<PaymentDto>(
      `${this.apiConfig.baseUrl}/billing/payments`,
      payload,
      { withCredentials: true },
    );
  }

  refundPayment(paymentId: string, propId: number, refundId?: string) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.post<PaymentDto>(
      `${this.apiConfig.baseUrl}/billing/payments/${paymentId}/refund`,
      refundId ? { refund_id: refundId } : {},
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
