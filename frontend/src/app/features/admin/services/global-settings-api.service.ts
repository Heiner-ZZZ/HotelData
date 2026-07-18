import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { map, Observable } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import type { PlatformConfigDto, HotelGlobalListDto, TaxRateDto, CommissionRateDto } from '../models/global-settings.dto';
import type { PlatformConfig, HotelGlobalList, TaxRate, CommissionRate } from '../models/global-settings.model';
import { mapPlatformConfig, mapHotelGlobalList, mapTaxRate, mapCommissionRate } from '../mappers/global-settings.mapper';

@Injectable({ providedIn: 'root' })
export class GlobalSettingsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly base = `${this.apiConfig.baseUrl}/admin/global-settings`;

  // ─── Platform Config ──────────────────────────────────────────────

  getConfig(): Observable<PlatformConfig> {
    return this.http
      .get<PlatformConfigDto>(`${this.base}/config`, { withCredentials: true })
      .pipe(map(mapPlatformConfig));
  }

  updateConfig(payload: Record<string, number>): Observable<PlatformConfig> {
    return this.http
      .put<PlatformConfigDto>(`${this.base}/config`, payload, { withCredentials: true })
      .pipe(map(mapPlatformConfig));
  }

  // ─── Hotels ───────────────────────────────────────────────────────

  listHotels(q = '', page = 1, pageSize = 50): Observable<HotelGlobalList> {
    const params = new HttpParams()
      .set('q', q)
      .set('page', String(page))
      .set('page_size', String(pageSize));
    return this.http
      .get<HotelGlobalListDto>(`${this.base}/hotels`, { params, withCredentials: true })
      .pipe(map(mapHotelGlobalList));
  }

  updateHotel(propId: number, payload: Record<string, string | null>): Observable<{ ok: boolean }> {
    return this.http.put<{ ok: boolean }>(`${this.base}/hotels/${propId}`, payload, { withCredentials: true });
  }

  // ─── Tax Rates ────────────────────────────────────────────────────

  listTaxRates(): Observable<TaxRate[]> {
    return this.http
      .get<{ items: TaxRateDto[] }>(`${this.base}/tax-rates`, { withCredentials: true })
      .pipe(map(r => r.items.map(mapTaxRate)));
  }

  createTaxRate(payload: Record<string, number | string>): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(`${this.base}/tax-rates`, payload, { withCredentials: true });
  }

  updateTaxRate(countryId: number, payload: Record<string, number | string>): Observable<{ ok: boolean }> {
    return this.http.put<{ ok: boolean }>(`${this.base}/tax-rates/${countryId}`, payload, { withCredentials: true });
  }

  deleteTaxRate(countryId: number): Observable<{ ok: boolean }> {
    return this.http.delete<{ ok: boolean }>(`${this.base}/tax-rates/${countryId}`, { withCredentials: true });
  }

  // ─── Commission Rates ─────────────────────────────────────────────

  listCommissionRates(): Observable<CommissionRate[]> {
    return this.http
      .get<{ items: CommissionRateDto[] }>(`${this.base}/commission-rates`, { withCredentials: true })
      .pipe(map(r => r.items.map(mapCommissionRate)));
  }

  createCommissionRate(payload: Record<string, number>): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(`${this.base}/commission-rates`, payload, { withCredentials: true });
  }

  updateCommissionRate(propId: number, payload: Record<string, number>): Observable<{ ok: boolean }> {
    return this.http.put<{ ok: boolean }>(`${this.base}/commission-rates/${propId}`, payload, { withCredentials: true });
  }

  deleteCommissionRate(propId: number): Observable<{ ok: boolean }> {
    return this.http.delete<{ ok: boolean }>(`${this.base}/commission-rates/${propId}`, { withCredentials: true });
  }
}
