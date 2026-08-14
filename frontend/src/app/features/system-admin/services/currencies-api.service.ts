import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import type { CurrencyDto } from '../models/currencies.dto';
import type { Currency } from '../models/currencies.model';
import { mapCurrency } from '../mappers/currencies.mapper';

@Injectable({ providedIn: 'root' })
export class CurrenciesApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  list(activeOnly = false): Observable<Currency[]> {
    return this.http
      .get<{ currencies: CurrencyDto[] }>(
        `${this.apiConfig.baseUrl}/management/currencies`,
        { params: { active_only: activeOnly }, withCredentials: true }
      )
      .pipe(map((res) => res.currencies.map(mapCurrency)));
  }

  /**
   * Monedas activas vía el endpoint público — sin permiso `settings.read`.
   * Lo usan páginas de gestión (ej. Editar Propiedad) donde un rol restringido
   * (gerente_hotel) necesita el catálogo para el select de moneda pero no tiene
   * acceso al catálogo administrativo (`/management/currencies` → 403).
   */
  listActivePublic(): Observable<Currency[]> {
    return this.http
      .get<{ currencies: CurrencyDto[] }>(`${this.apiConfig.baseUrl}/public/currencies`)
      .pipe(map((res) => res.currencies.map(mapCurrency)));
  }

  get(code: string): Observable<Currency> {
    return this.http
      .get<CurrencyDto>(`${this.apiConfig.baseUrl}/management/currencies/${code}`, {
        withCredentials: true,
      })
      .pipe(map(mapCurrency));
  }

  create(currency: { code: string; name: string; symbol: string; decimals: number }): Observable<Currency> {
    return this.http
      .post<CurrencyDto>(`${this.apiConfig.baseUrl}/management/currencies`, currency, {
        withCredentials: true,
      })
      .pipe(map(mapCurrency));
  }

  update(code: string, currency: { name: string; symbol: string; decimals: number }): Observable<Currency> {
    return this.http
      .put<CurrencyDto>(`${this.apiConfig.baseUrl}/management/currencies/${code}`, currency, {
        withCredentials: true,
      })
      .pipe(map(mapCurrency));
  }

  toggle(code: string): Observable<Currency> {
    return this.http
      .patch<CurrencyDto>(`${this.apiConfig.baseUrl}/management/currencies/${code}/toggle`, {}, {
        withCredentials: true,
      })
      .pipe(map(mapCurrency));
  }

  delete(code: string): Observable<void> {
    return this.http.delete<void>(`${this.apiConfig.baseUrl}/management/currencies/${code}`, {
      withCredentials: true,
    });
  }
}
