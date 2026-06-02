import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapAuditActivity } from '../mappers/audit.mapper';
import type { AuditActivityDto } from '../models/audit.dto';

@Injectable({ providedIn: 'root' })
export class AuditApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getActivity() {
    return this.http
      .get<AuditActivityDto>(`${this.apiConfig.baseUrl}/audit/activity`, {
        withCredentials: true,
      })
      .pipe(map((dto) => mapAuditActivity(dto)));
  }
}
