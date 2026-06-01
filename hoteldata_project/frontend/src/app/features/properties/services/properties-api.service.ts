import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapPropertyDetailResponse, mapPropertiesListResponse } from '../mappers/properties.mapper';
import type { PropertyDetailResponseDto, PropertiesListResponseDto } from '../models/properties.dto';

@Injectable({
  providedIn: 'root'
})
export class PropertiesApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getProperties(query: string, page: number) {
    let params = new HttpParams().set('page', page);
    if (query.trim()) {
      params = params.set('q', query.trim());
    }

    return this.http
      .get<PropertiesListResponseDto>(`${this.apiConfig.baseUrl}/management/properties`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapPropertiesListResponse(dto)));
  }

  getPropertyDetail(propId: number) {
    return this.http
      .get<PropertyDetailResponseDto>(`${this.apiConfig.baseUrl}/management/properties/${propId}`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapPropertyDetailResponse(dto)));
  }
}
