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

  private propParams(propId?: number): HttpParams {
    return propId && propId > 0 ? new HttpParams().set('prop_id', String(propId)) : new HttpParams();
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

  getItem(itemId: string, propId: number) {
    return this.http.get<LostItemResponseDto>(`${this.baseUrl}/${itemId}`, { params: this.propParams(propId), withCredentials: true });
  }

  createItem(payload: LostItemCreateDto, propId: number) {
    return this.http.post<LostItemResponseDto>(this.baseUrl, payload, { params: this.propParams(propId), withCredentials: true });
  }

  updateItem(itemId: string, payload: Partial<LostItemCreateDto>, propId: number) {
    return this.http.put<LostItemResponseDto>(`${this.baseUrl}/${itemId}`, payload, { params: this.propParams(propId), withCredentials: true });
  }

  deleteItem(itemId: string, propId: number) {
    return this.http.delete<LostItemResponseDto>(`${this.baseUrl}/${itemId}`, { params: this.propParams(propId), withCredentials: true });
  }

  claimItem(itemId: string, returnedTo: string, propId: number, notes = '') {
    return this.http.post<LostItemResponseDto>(
      `${this.baseUrl}/${itemId}/claim`,
      { returned_to: returnedTo, notes },
      { params: this.propParams(propId), withCredentials: true },
    );
  }

  disposeItem(itemId: string, propId: number, notes = '') {
    return this.http.post<LostItemResponseDto>(
      `${this.baseUrl}/${itemId}/dispose`,
      { notes },
      { params: this.propParams(propId), withCredentials: true },
    );
  }
}
