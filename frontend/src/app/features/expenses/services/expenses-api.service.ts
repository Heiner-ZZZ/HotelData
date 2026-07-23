import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

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

  getDashboard() {
    return this.http.get<any>(`${this.apiConfig.baseUrl}/expenses/dashboard`, { withCredentials: true })
      .pipe(map(dto => mapExpenseDashboard(dto)));
  }

  getInvoices(status?: string, category?: string, vendor?: string, page = 1) {
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

  postFolioPayment(folioId: string, amount: number, method: string, notes: string) {
    return this.http.post<{ folio_id: string; new_balance: number; payment_amount: number; method: string }>(
      `${this.apiConfig.baseUrl}/expenses/ledger/folios/${folioId}/payment`,
      { amount, method, notes },
      { withCredentials: true },
    );
  }

  transferFolioCharges(folioId: string, targetFolioId: string, amount: number, notes: string) {
    return this.http.post<{ source_folio_id: string; source_new_balance: number; target_folio_id: string; target_new_balance: number; amount: number }>(
      `${this.apiConfig.baseUrl}/expenses/ledger/folios/${folioId}/transfer`,
      { target_folio_id: targetFolioId, amount, notes },
      { withCredentials: true },
    );
  }

  getFolioPostings(folioId: string) {
    return this.http.get<FolioPostingsDto>(`${this.apiConfig.baseUrl}/expenses/ledger/folios/${folioId}/postings`, { withCredentials: true })
      .pipe(map(dto => mapFolioPostings(dto)));
  }
}
