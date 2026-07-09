import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';

export interface GuestItem {
  guest_name: string;
  guest_email: string;
  guest_phone: string;
  total_bookings: number;
  last_booking_date: string;
  total_spent: number;
  last_status: string;
}

export interface GuestsResponse {
  items: GuestItem[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class GuestsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  listGuests(propId: number, q = '', page = 1, pageSize = 20) {
    const params = new HttpParams()
      .set('prop_id', String(propId))
      .set('q', q)
      .set('page', String(page))
      .set('page_size', String(pageSize));
    return this.http
      .get<GuestsResponse>(`${this.apiConfig.baseUrl}/management/guests`, {
        params,
        withCredentials: true,
      });
  }
}
