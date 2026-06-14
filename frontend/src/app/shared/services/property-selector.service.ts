import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../core/api/api.config';
import type { PropertyOption, PropertyOptionsPage } from '../models/property-option.model';

interface PropertiesOptionsDto {
  properties: Array<{ prop_id: number; display_name: string }>;
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
      );
  }
}
