import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapExpenseDashboard, mapInvoiceDetail, mapInvoiceList } from '../mappers/expenses.mapper';
import type { InvoiceDetailDto, InvoiceListDto } from '../models/expenses.dto';

@Injectable({ providedIn: 'root' })
export class ExpensesApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getDashboard() {
    return this.http.get<any>(`${this.apiConfig.baseUrl}/expenses/dashboard`, { withCredentials: true })
      .pipe(map(dto => mapExpenseDashboard(dto)));
  }

  getInvoices(status?: string, category?: string, vendor?: string, page: number = 1) {
    let params = new HttpParams().set('page', String(page));
    if (status) params = params.set('status', status);
    if (category) params = params.set('category', category);
    if (vendor) params = params.set('vendor', vendor);
    return this.http.get<InvoiceListDto>(`${this.apiConfig.baseUrl}/expenses/invoices`, { params, withCredentials: true })
      .pipe(map(dto => mapInvoiceList(dto)));
  }

  getInvoice(id: string) {
    return this.http.get<InvoiceDetailDto>(`${this.apiConfig.baseUrl}/expenses/invoices/${id}`, { withCredentials: true })
      .pipe(map(dto => mapInvoiceDetail(dto)));
  }

  createInvoice(payload: any) {
    return this.http.post(`${this.apiConfig.baseUrl}/expenses/invoices`, payload, { withCredentials: true });
  }

  updateInvoice(id: string, payload: any) {
    return this.http.put(`${this.apiConfig.baseUrl}/expenses/invoices/${id}`, payload, { withCredentials: true });
  }

  deleteInvoice(id: string) {
    return this.http.delete(`${this.apiConfig.baseUrl}/expenses/invoices/${id}`, { withCredentials: true });
  }

  getCategories() {
    return this.http.get<any[]>(`${this.apiConfig.baseUrl}/expenses/categories`, { withCredentials: true });
  }
}
