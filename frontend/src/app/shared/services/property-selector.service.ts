import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, catchError, of } from 'rxjs';

import { getErrorStatus } from '../utils/http-error.util';
import { API_CONFIG } from '../../core/api/api.config';
import type { PropertyOption, PropertyOptionsPage } from '../models/property-option.model';

interface PropertiesOptionsDto {
  properties: { prop_id: number; display_name: string }[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

@Injectable({ providedIn: 'root' })
export class PropertySelectorService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getOptions(q?: string, page?: number, pageSize?: number) {
    let params = new HttpParams();
    if (q != null) params = params.set('q', q);
    if (page != null) params = params.set('page', String(page));
    if (pageSize != null) params = params.set('page_size', String(pageSize));
    return this.http
      .get<PropertiesOptionsDto>(`${this.apiConfig.baseUrl}/management/properties/options`, {
        params,
        withCredentials: true,
      })
      .pipe(
        map(
          (dto): PropertyOptionsPage => ({
            items: dto.properties.map((p) => ({
              propId: p.prop_id,
              label: p.display_name || `Hotel ${p.prop_id}`,
            })),
            total: dto.total,
            page: dto.page,
            pageSize: dto.page_size,
            hasNext: dto.has_next,
          }),
        ),
        catchError((err: unknown) => {
          // getErrorStatus cubre HttpErrorResponse (tests) y ApiError del interceptor (vivo).
          if (getErrorStatus(err) === 401) {
            // Session expired — signal to the component so it can show
            // a login prompt instead of a broken dropdown.
            return of({
              items: [] as PropertyOption[],
              total: 0,
              page: 1,
              pageSize: 10,
              hasNext: false,
              authRequired: true,
            });
          }
          // Any other error: return empty results gracefully
          return of({
            items: [] as PropertyOption[],
            total: 0,
            page: 1,
            pageSize: 10,
            hasNext: false,
            authRequired: false,
          });
        }),
      );
  }
}
