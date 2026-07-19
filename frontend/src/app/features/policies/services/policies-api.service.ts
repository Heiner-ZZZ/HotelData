import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { catchAuthError } from '../../../shared/utils/catch-auth-error';
import { mapPolicies, mapPoliciesOptions } from '../mappers/policies.mapper';
import type { PoliciesDto, PoliciesOptionsDto, PoliciesSaveDto } from '../models/policies.dto';

@Injectable({
  providedIn: 'root'
})
export class PoliciesApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getOptions(q?: string, page?: number, pageSize?: number) {
    let params = new HttpParams();
    if (q != null) params = params.set('q', q);
    if (page != null) params = params.set('page', String(page));
    if (pageSize != null) params = params.set('page_size', String(pageSize));
    return this.http
      .get<PoliciesOptionsDto>(`${this.apiConfig.baseUrl}/management/policies/options`, {
        params,
        withCredentials: true
      })
      .pipe(catchAuthError(), map((dto) => mapPoliciesOptions(dto)));
  }

  getPolicies(propId: number, roomTypeId?: string, ratePlanId?: string) {
    let params = new HttpParams().set('prop_id', String(propId));
    if (roomTypeId) {
      params = params.set('room_type_id', roomTypeId);
    }
    if (ratePlanId) {
      params = params.set('rate_plan_id', ratePlanId);
    }
    return this.http
      .get<PoliciesDto>(`${this.apiConfig.baseUrl}/management/policies`, {
        params,
        withCredentials: true
      })
      .pipe(catchAuthError(), map((dto) => mapPolicies(dto)));
  }

  savePolicies(payload: PoliciesSaveDto) {
    return this.http.put(`${this.apiConfig.baseUrl}/management/policies`, payload, {
      withCredentials: true
    });
  }
}
