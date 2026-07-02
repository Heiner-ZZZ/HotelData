import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapInvoiceDetail, mapInvoicesList, mapPaymentsList } from '../mappers/billing.mapper';
import type { InvoiceDetailDto, InvoiceStatsDto, InvoicesListDto, PaymentsListDto } from '../models/billing.dto';
import type { InvoiceStats } from '../models/billing.model';

@Injectable({ providedIn: 'root' })
export class BillingApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getInvoices(page: number, filters?: { prop_id?: number; status?: string; q?: string; date_from?: string; date_to?: string }) {
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

  getInvoiceStats() {
    return this.http.get<InvoiceStatsDto>(
      `${this.apiConfig.baseUrl}/billing/invoices/stats`,
      { withCredentials: true },
    );
  }

  getInvoiceDetail(invoiceId: string) {
    return this.http
      .get<InvoiceDetailDto>(`${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}`, { withCredentials: true })
      .pipe(map(dto => mapInvoiceDetail(dto)));
  }

  cancelInvoice(invoiceId: string) {
    return this.http.post(`${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}/cancel`, {}, { withCredentials: true });
  }

  getPayments(page: number, filters?: { prop_id?: number }) {
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

  /** Add a line item to an invoice (only if status='issued'). */
  addLineItem(invoiceId: string, payload: { name: string; quantity?: number; unit_price?: number; category?: string }) {
    return this.http.post<InvoiceDetailDto>(
      `${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}/items`,
      payload,
      { withCredentials: true },
    ).pipe(map(dto => mapInvoiceDetail(dto)));
  }

  /** Remove a line item from an invoice (only if status='issued'). Cannot remove room charge. */
  removeLineItem(invoiceId: string, itemId: string) {
    return this.http.delete<InvoiceDetailDto>(
      `${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}/items/${itemId}`,
      { withCredentials: true },
    ).pipe(map(dto => mapInvoiceDetail(dto)));
  }

  payInvoice(invoiceId: string) {
    return this.http.post<{ ok: boolean; message: string; payment: Record<string, unknown> }>(
      `${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}/pay`,
      {},
      { withCredentials: true },
    );
  }

  refundPayment(paymentId: string) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/billing/payments/${paymentId}/refund`,
      {},
      { withCredentials: true },
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
