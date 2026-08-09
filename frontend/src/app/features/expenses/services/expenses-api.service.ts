import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, throwError } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapExpenseDashboard, mapInvoiceDetail, mapInvoiceList, mapLedgerFolios, mapLedgerSummary, mapTrialBalance, mapIncomeStatement, mapBalanceSheet, mapChartAccounts, mapFolioPostings } from '../mappers/expenses.mapper';
import type { InvoiceDetailDto, InvoiceListDto } from '../models/expenses.dto';
import type { LedgerFoliosDto, LedgerSummaryDto, TrialBalanceDto, IncomeStatementDto, BalanceSheetDto, ChartAccountDto, FolioPostingsDto } from '../models/ledger.dto';

/**
 * Page size for ledger transaction lists (both the service method and the
 * httpResource in ledger-page.ts).
 *
 * Deliberately set to 100 (vs. backend default 50) because the AG Grid
 * ledger view benefits from higher row density to reduce pagination.
 * The backend ceiling is 200, so this is well within bounds.
 */
export const DEFAULT_LEDGER_PAGE_SIZE = 100;

@Injectable({ providedIn: 'root' })
export class ExpensesApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getDashboard(propId: number) {
    if (!propId || propId < 1) {
      return throwError(() => new Error('Selecciona un hotel para consultar Vendor AP.'));
    }
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.get<any>(`${this.apiConfig.baseUrl}/expenses/dashboard`, { params, withCredentials: true })
      .pipe(map(dto => mapExpenseDashboard(dto)));
  }

  getInvoices(status?: string, category?: string, vendor?: string, page = 1, propId?: number) {
    if (!propId || propId < 1) {
      return throwError(() => new Error('Selecciona un hotel para consultar Vendor AP.'));
    }
    let params = new HttpParams().set('page', String(page));
    if (status) params = params.set('status', status);
    if (category) params = params.set('category', category);
    if (vendor) params = params.set('vendor', vendor);
    if (propId) params = params.set('prop_id', String(propId));
    const url = `${this.apiConfig.baseUrl}/hotels/${propId}/vendor-ap/invoices`;
    params = params.set('page_size', '20');
    return this.http.get<InvoiceListDto>(url, { params, withCredentials: true })
      .pipe(map(dto => mapInvoiceList(dto)));
  }

  getInvoice(id: string, propId?: number) {
    if (!propId || propId < 1) {
      return throwError(() => new Error('Selecciona un hotel para consultar Vendor AP.'));
    }
    const url = `${this.apiConfig.baseUrl}/hotels/${propId}/vendor-ap/invoices/${id}`;
    return this.http.get<InvoiceDetailDto>(url, { withCredentials: true })
      .pipe(map(dto => mapInvoiceDetail(dto)));
  }

  createInvoice(payload: any) {
    return this.http.post(`${this.apiConfig.baseUrl}/expenses/invoices`, payload, { withCredentials: true });
  }

  updateInvoice(id: string, payload: any, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.put(`${this.apiConfig.baseUrl}/expenses/invoices/${id}`, payload, { params, withCredentials: true });
  }

  payInvoice(id: string, propId: number, method = 'bank_transfer', paymentReference = `UI-${id}`) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.post(`${this.apiConfig.baseUrl}/expenses/invoices/${id}/pay`, {
      method,
      payment_reference: paymentReference,
    }, { params, withCredentials: true });
  }

  deleteInvoice(id: string, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.delete(`${this.apiConfig.baseUrl}/expenses/invoices/${id}`, { params, withCredentials: true });
  }

  getCategories(propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.get<any[]>(`${this.apiConfig.baseUrl}/expenses/categories`, { params, withCredentials: true });
  }

  // ─── Ledger ───

  getLedgerPeriods(propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.get<string[]>(`${this.apiConfig.baseUrl}/expenses/ledger/periods`, { params, withCredentials: true });
  }

  getLedgerFolios(propId: number, status?: string) {
    let params = new HttpParams().set('prop_id', String(propId));
    if (status) params = params.set('status', status);
    return this.http.get<LedgerFoliosDto>(`${this.apiConfig.baseUrl}/expenses/ledger/folios`, { params, withCredentials: true })
      .pipe(map(dto => mapLedgerFolios(dto)));
  }

  getLedgerSummary(propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.get<LedgerSummaryDto>(`${this.apiConfig.baseUrl}/expenses/ledger/summary`, { params, withCredentials: true })
      .pipe(map(dto => mapLedgerSummary(dto)));
  }

  getTrialBalance(propId: number, period?: string) {
    let params = new HttpParams().set('prop_id', String(propId));
    if (period) params = params.set('accounting_period', period);
    return this.http.get<TrialBalanceDto>(`${this.apiConfig.baseUrl}/expenses/ledger/trial-balance`, { params, withCredentials: true })
      .pipe(map(dto => mapTrialBalance(dto)));
  }

  getIncomeStatement(propId: number, period?: string) {
    let params = new HttpParams().set('prop_id', String(propId));
    if (period) params = params.set('accounting_period', period);
    return this.http.get<IncomeStatementDto>(`${this.apiConfig.baseUrl}/expenses/ledger/income-statement`, { params, withCredentials: true })
      .pipe(map(dto => mapIncomeStatement(dto)));
  }

  getBalanceSheet(propId: number, period?: string) {
    let params = new HttpParams().set('prop_id', String(propId));
    if (period) params = params.set('accounting_period', period);
    return this.http.get<BalanceSheetDto>(`${this.apiConfig.baseUrl}/expenses/ledger/balance-sheet`, { params, withCredentials: true })
      .pipe(map(dto => mapBalanceSheet(dto)));
  }

  getChartOfAccounts() {
    return this.http.get<ChartAccountDto[]>(`${this.apiConfig.baseUrl}/expenses/ledger/accounts`, { withCredentials: true })
      .pipe(map(dtos => mapChartAccounts(dtos)));
  }

  // ─── Folio Payments ───

  postFolioPayment(folioId: string, amount: number, method: string, notes: string, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.post<{ folio_id: string; new_balance: number; payment_amount: number; method: string }>(
      `${this.apiConfig.baseUrl}/expenses/ledger/folios/${folioId}/payment`,
      { amount, method, notes },
      { params, withCredentials: true },
    );
  }

  transferFolioCharges(folioId: string, targetFolioId: string, amount: number, notes: string, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.post<{ source_folio_id: string; source_new_balance: number; target_folio_id: string; target_new_balance: number; amount: number }>(
      `${this.apiConfig.baseUrl}/expenses/ledger/folios/${folioId}/transfer`,
      { target_folio_id: targetFolioId, amount, notes },
      { params, withCredentials: true },
    );
  }

  getFolioPostings(folioId: string, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.get<FolioPostingsDto>(`${this.apiConfig.baseUrl}/expenses/ledger/folios/${folioId}/postings`, { params, withCredentials: true })
      .pipe(map(dto => mapFolioPostings(dto)));
  }

}
