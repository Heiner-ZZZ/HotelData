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
}
