import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapDashboardResponse } from '../mappers/dashboard.mapper';
import type { DashboardApiResponseDto, DashboardKpisResponseDto } from '../models/dashboard.dto';

@Injectable({
  providedIn: 'root'
})
export class DashboardApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getOverview() {
    return this.http
      .get<DashboardApiResponseDto>(`${this.apiConfig.baseUrl}/dashboard/overview`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapDashboardResponse(dto)));
  }

  getKpis() {
    return this.http
      .get<DashboardKpisResponseDto>(`${this.apiConfig.baseUrl}/dashboard/kpis`, {
        withCredentials: true
      })
      .pipe(map((dto) => dto.payload ? mapDashboardResponse(dto.payload) : null));
  }

  refreshKpis() {
    return this.http.post<{ ok: boolean; display_message: string }>(
      `${this.apiConfig.baseUrl}/dashboard/kpis/refresh`,
      {},
      { withCredentials: true }
    );
  }
}
