import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapInvoiceDetail, mapInvoicesList, mapPaymentsList } from '../mappers/billing.mapper';
import type { InvoiceDetailDto, InvoicesListDto, PaymentsListDto } from '../models/billing.dto';

@Injectable({ providedIn: 'root' })
export class BillingApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getInvoices(page: number) {
    const params = new HttpParams().set('page', String(page));
    return this.http
      .get<InvoicesListDto>(`${this.apiConfig.baseUrl}/billing/invoices`, { params, withCredentials: true })
      .pipe(map(dto => mapInvoicesList(dto)));
  }

  getInvoiceDetail(invoiceId: string) {
    return this.http
      .get<InvoiceDetailDto>(`${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}`, { withCredentials: true })
      .pipe(map(dto => mapInvoiceDetail(dto)));
  }

  cancelInvoice(invoiceId: string) {
    return this.http.post(`${this.apiConfig.baseUrl}/billing/invoices/${invoiceId}/cancel`, {}, { withCredentials: true });
  }

  getPayments(page: number) {
    const params = new HttpParams().set('page', String(page));
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
