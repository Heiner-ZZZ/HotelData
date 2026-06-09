import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapManagementReports } from '../mappers/management-reports.mapper';
import type { ManagementReportsDto } from '../models/management-reports.dto';

@Injectable({
  providedIn: 'root'
})
export class ManagementReportsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getReports() {
    return this.http
      .get<ManagementReportsDto>(`${this.apiConfig.baseUrl}/management/reports`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapManagementReports(dto)));
  }
}
