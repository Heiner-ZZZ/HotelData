import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapCheckOuts } from '../mappers/check-outs.mapper';
import type { CheckOutsDto } from '../models/check-outs.dto';

export interface DateHistoryEntry {
  date: string;
  count: number;
  prop_id?: number;
  hotel_label?: string;
}

export interface BookingCharge {
  concept: string;
  amount: number;
  quantity: number;
  total: number;
  note: string;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class CheckOutsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getCheckOuts(operationDate: string, propId?: number) {
    let params = new HttpParams().set('date', operationDate);
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http
      .get<CheckOutsDto>(`${this.apiConfig.baseUrl}/management/check-outs`, { params, withCredentials: true })
      .pipe(map((dto) => mapCheckOuts(dto)));
  }

  getCheckOutDates(propId?: number) {
    let params = new HttpParams();
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http.get<DateHistoryEntry[]>(`${this.apiConfig.baseUrl}/management/check-outs/dates`, {
      params,
      withCredentials: true
    });
  }

  /** Fetch additional charges (consumptions) for a booking before checkout. */
  getBookingCharges(bookingId: string) {
    const params = new HttpParams().set('booking_id', bookingId);
    return this.http.get<{
      items: BookingCharge[];
      total: number;
      page: number;
      page_size: number;
      total_pages: number;
      has_next: boolean;
      has_prev: boolean;
    }>(`${this.apiConfig.baseUrl}/housekeeping/charges`, { params, withCredentials: true });
  }

  /** Create an additional charge for a booking before checkout. */
  createCharge(bookingId: string, propId: number, concept: string, amount: number, quantity: number, note: string = '') {
    return this.http.post<BookingCharge>(
      `${this.apiConfig.baseUrl}/housekeeping/charges`,
      { booking_id: bookingId, prop_id: propId, concept, amount, quantity, note },
      { withCredentials: true }
    );
  }

  completeCheckOut(bookingId: string) {
    return this.http.post(`${this.apiConfig.baseUrl}/management/check-outs/${bookingId}/complete`, {}, { withCredentials: true });
  }
}
