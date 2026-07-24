import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

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

export interface GuestBookingItem {
  booking_id: string;
  check_in_date: string;
  check_out_date: string;
  total_price: number | null;
  currency: string;
  status: string;
  payment_status: string;
  guest_name: string;
  adults: number;
  children: number;
  rooms: number;
  created_at: string;
  booking_source: string;
}

export interface GuestBookingsResponse {
  guest_email: string;
  guest_name: string;
  prop_id: number;
  total_bookings: number;
  items: GuestBookingItem[];
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

  getGuestBookings(guestEmail: string, propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.get<GuestBookingsResponse>(
      `${this.apiConfig.baseUrl}/management/guests/${encodeURIComponent(guestEmail)}/bookings`,
      { params, withCredentials: true }
    );
  }
}
