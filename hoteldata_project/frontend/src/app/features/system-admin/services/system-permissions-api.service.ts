import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapSystemPermissionsResponse } from '../mappers/system-permissions.mapper';
import type { SystemPermissionsResponseDto } from '../models/system-permissions.dto';

@Injectable({
  providedIn: 'root'
})
export class SystemPermissionsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getPermissionsOverview() {
    return this.http
      .get<SystemPermissionsResponseDto>(`${this.apiConfig.baseUrl}/admin/permissions`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapSystemPermissionsResponse(dto)));
  }
}
