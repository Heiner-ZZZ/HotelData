import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapSystemUserToggleResult, mapSystemUsersResponse } from '../mappers/system-users.mapper';
import type { SystemUserToggleResponseDto, SystemUsersResponseDto } from '../models/system-users.dto';

@Injectable({
  providedIn: 'root'
})
export class SystemUsersApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getUsers() {
    return this.http
      .get<SystemUsersResponseDto>(`${this.apiConfig.baseUrl}/admin/users`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapSystemUsersResponse(dto)));
  }

  toggleUserActive(userId: string) {
    return this.http
      .post<SystemUserToggleResponseDto>(
        `${this.apiConfig.baseUrl}/admin/users/${userId}/toggle-active`,
        {},
        { withCredentials: true }
      )
      .pipe(map((dto) => mapSystemUserToggleResult(dto)));
  }
}
