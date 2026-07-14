import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { catchAuthError } from '../../../shared/utils/catch-auth-error';
import { mapDashboardResponse } from '../mappers/dashboard.mapper';
import type { DashboardApiResponseDto, DashboardKpisResponseDto } from '../models/dashboard.dto';

@Injectable({
  providedIn: 'root'
})
export class DashboardApiService {
  private readonly http = inject(HttpClient);

  getOverview() {
    return this.http
      .get<DashboardApiResponseDto>('/dashboard/overview')
      .pipe(catchAuthError(), map((dto) => mapDashboardResponse(dto)));
  }

  getKpis() {
    return this.http
      .get<DashboardKpisResponseDto>('/dashboard/kpis')
      .pipe(catchAuthError(), map((dto) => dto.payload ? mapDashboardResponse(dto.payload) : null));
  }

  refreshKpis() {
    return this.http.post<{ ok: boolean; display_message: string }>('/dashboard/kpis/refresh', {});
  }
}
