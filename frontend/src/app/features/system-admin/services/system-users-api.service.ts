import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapSystemUserToggleResult, mapSystemUsersResponse } from '../mappers/system-users.mapper';
import type {
  HotelSearchResultDto,
  SystemUserToggleResponseDto,
  SystemUserUpdatePayloadDto,
  SystemUserUpdateResponseDto,
  SystemUsersResponseDto,
} from '../models/system-users.dto';

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

  deleteUser(userId: string) {
    return this.http
      .delete<{ ok: boolean; message: string }>(
        `${this.apiConfig.baseUrl}/admin/users/${userId}`,
        { withCredentials: true }
      );
  }

  updateUser(userId: string, payload: SystemUserUpdatePayloadDto) {
    return this.http
      .put<SystemUserUpdateResponseDto>(
        `${this.apiConfig.baseUrl}/admin/users/${userId}`,
        payload,
        { withCredentials: true }
      );
  }

  searchHotels(query: string) {
    return this.http
      .get<{ items: HotelSearchResultDto[]; has_next: boolean }>(
        `${this.apiConfig.baseUrl}/admin/ownership/hotels/search`,
        { params: { q: query, page: '1', page_size: '20' }, withCredentials: true }
      )
      .pipe(
        map((res) =>
          (res.items || []).map((h) => ({ propId: h.prop_id, label: h.label }))
        )
      );
  }
}
