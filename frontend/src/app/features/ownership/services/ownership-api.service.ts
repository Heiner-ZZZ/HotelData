import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapCreateUserResponse, mapHotelSearchResponse, mapOwnershipUserDetailResponse, mapOwnershipUsersResponse, mapUpdateHotelsResponse } from '../mappers/ownership.mapper';
import type { HotelSearchResponseDto, OwnershipCreateResponseDto, OwnershipUpdateHotelsResponseDto, OwnershipUserDetailResponseDto, OwnershipUsersResponseDto } from '../models/ownership.dto';

@Injectable({
  providedIn: 'root'
})
export class OwnershipApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  private readonly base = `${this.apiConfig.baseUrl}/admin/ownership`;

  getUsers() {
    return this.http
      .get<OwnershipUsersResponseDto>(`${this.base}/users`, { withCredentials: true })
      .pipe(map(dto => mapOwnershipUsersResponse(dto)));
  }

  getUserDetail(userId: string) {
    return this.http
      .get<OwnershipUserDetailResponseDto>(`${this.base}/users/${userId}`, { withCredentials: true })
      .pipe(map(dto => mapOwnershipUserDetailResponse(dto)));
  }

  createUser(data: {
    username: string;
    email: string;
    password: string;
    primary_role: string;
    display_name?: string;
    assigned_hotels?: number[];
  }) {
    return this.http
      .post<OwnershipCreateResponseDto>(`${this.base}/users`, data, { withCredentials: true })
      .pipe(map(dto => mapCreateUserResponse(dto)));
  }

  updateAssignedHotels(userId: string, assignedHotels: number[]) {
    return this.http
      .put<OwnershipUpdateHotelsResponseDto>(
        `${this.base}/users/${userId}/assigned-hotels`,
        { assigned_hotels: assignedHotels },
        { withCredentials: true }
      )
      .pipe(map(dto => mapUpdateHotelsResponse(dto)));
  }

  getRoles() {
    return this.http
      .get<{ roles: { role_name: string; description: string }[] }>(`${this.base}/roles`, { withCredentials: true })
      .pipe(map(dto => dto.roles.map(r => ({ roleName: r.role_name, description: r.description }))));
  }

  searchHotels(query: string, page = 1, pageSize = 20) {
    return this.http
      .get<HotelSearchResponseDto>(`${this.base}/hotels/search`, {
        params: { q: query, page: String(page), page_size: String(pageSize) },
        withCredentials: true
      })
      .pipe(map(dto => mapHotelSearchResponse(dto)));
  }
}
