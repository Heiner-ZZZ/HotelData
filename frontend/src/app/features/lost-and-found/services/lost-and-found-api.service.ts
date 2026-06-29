import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { API_CONFIG } from '../../../core/api/api.config';
import type { LostItemCreateDto, LostItemResponseDto, PaginatedResponse } from '../models/lost-and-found.dto';

@Injectable({ providedIn: 'root' })
export class LostAndFoundApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  private get baseUrl() {
    return `${this.apiConfig.baseUrl}/lost-and-found`;
  }

  listItems(params?: {
    propId?: number;
    status?: string;
    bookingId?: string;
    search?: string;
    page?: number;
  }) {
    let httpParams = new HttpParams();
    if (params) {
      if (params.propId) httpParams = httpParams.set('prop_id', String(params.propId));
      if (params.status) httpParams = httpParams.set('status', params.status);
      if (params.bookingId) httpParams = httpParams.set('booking_id', params.bookingId);
      if (params.search) httpParams = httpParams.set('search', params.search);
      if (params.page) httpParams = httpParams.set('page', String(params.page));
    }
    return this.http.get<PaginatedResponse<LostItemResponseDto>>(this.baseUrl, {
      params: httpParams,
      withCredentials: true,
    });
  }

  getItem(itemId: string) {
    return this.http.get<LostItemResponseDto>(`${this.baseUrl}/${itemId}`, { withCredentials: true });
  }

  createItem(payload: LostItemCreateDto) {
    return this.http.post<LostItemResponseDto>(this.baseUrl, payload, { withCredentials: true });
  }

  updateItem(itemId: string, payload: Partial<LostItemCreateDto>) {
    return this.http.put<LostItemResponseDto>(`${this.baseUrl}/${itemId}`, payload, { withCredentials: true });
  }

  deleteItem(itemId: string) {
    return this.http.delete<LostItemResponseDto>(`${this.baseUrl}/${itemId}`, { withCredentials: true });
  }

  claimItem(itemId: string, returnedTo: string, notes = '') {
    return this.http.post<LostItemResponseDto>(
      `${this.baseUrl}/${itemId}/claim`,
      { returned_to: returnedTo, notes },
      { withCredentials: true },
    );
  }

  disposeItem(itemId: string, notes = '') {
    return this.http.post<LostItemResponseDto>(
      `${this.baseUrl}/${itemId}/dispose`,
      { notes },
      { withCredentials: true },
    );
  }
}
