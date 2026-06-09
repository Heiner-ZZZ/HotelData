import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapPolicies, mapPoliciesOptions } from '../mappers/policies.mapper';
import type { PoliciesDto, PoliciesOptionsDto, PoliciesSaveDto } from '../models/policies.dto';

@Injectable({
  providedIn: 'root'
})
export class PoliciesApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getOptions() {
    return this.http
      .get<PoliciesOptionsDto>(`${this.apiConfig.baseUrl}/management/policies/options`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapPoliciesOptions(dto)));
  }

  getPolicies(propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http
      .get<PoliciesDto>(`${this.apiConfig.baseUrl}/management/policies`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapPolicies(dto)));
  }

  savePolicies(payload: PoliciesSaveDto) {
    return this.http.put(`${this.apiConfig.baseUrl}/management/policies`, payload, {
      withCredentials: true
    });
  }
}
