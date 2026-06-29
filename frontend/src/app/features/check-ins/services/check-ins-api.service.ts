import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { catchAuthError } from '../../../shared/utils/catch-auth-error';
import { mapCheckIns } from '../mappers/check-ins.mapper';
import type { CheckInsDto } from '../models/check-ins.dto';

export interface DateHistoryEntry {
  date: string;
  count: number;
  prop_id?: number;
  hotel_label?: string;
}

@Injectable({ providedIn: 'root' })
export class CheckInsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getCheckIns(operationDate: string, propId?: number) {
    let params = new HttpParams().set('date', operationDate);
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http
      .get<CheckInsDto>(`${this.apiConfig.baseUrl}/management/check-ins`, { params, withCredentials: true })
      .pipe(catchAuthError(), map((dto) => mapCheckIns(dto)));
  }

  getCheckInDates(propId?: number) {
    let params = new HttpParams();
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http.get<DateHistoryEntry[]>(`${this.apiConfig.baseUrl}/management/check-ins/dates`, {
      params,
      withCredentials: true
    }).pipe(catchAuthError());
  }

  completeCheckIn(bookingId: string) {
    return this.http.post(`${this.apiConfig.baseUrl}/management/check-ins/${bookingId}/complete`, {}, { withCredentials: true });
  }

  /** Update check-in date/time using the shared PATCH /api/reservations/{id} endpoint */
  updateCheckInDateTime(bookingId: string, checkInDate?: string, checkInTime?: string) {
    const payload: Record<string, string> = {};
    if (checkInDate !== undefined) payload['check_in_date'] = checkInDate;
    if (checkInTime !== undefined) payload['check_in_time'] = checkInTime;
    return this.http.patch<{ booking_id: string; updated: boolean }>(
      `${this.apiConfig.baseUrl}/reservations/${bookingId}`,
      payload,
      { withCredentials: true }
    );
  }

  /** ═══ Check-In Detail Page ═══ */

  /** Fetch all check-in detail data for the detailed check-in page. */
  getCheckInDetail(bookingId: string) {
    return this.http.get<CheckInDetailDto>(
      `${this.apiConfig.baseUrl}/management/check-ins/${bookingId}/detail`,
      { withCredentials: true }
    );
  }

  /** Save check-in detail fields incrementally (draft). */
  saveCheckInDetail(bookingId: string, payload: Partial<CheckInDetailSavePayload>) {
    return this.http.patch<{ booking_id: string; updated: boolean; fields_updated: string[] }>(
      `${this.apiConfig.baseUrl}/management/check-ins/${bookingId}/detail`,
      payload,
      { withCredentials: true }
    );
  }

  /** Complete check-in with all detail data. */
  completeCheckInWithDetail(bookingId: string, payload: Partial<CheckInDetailSavePayload> & { payment_method?: string }) {
    return this.http.post<{ booking_id: string; stay_status: string; folio?: string; invoice_id?: string }>(
      `${this.apiConfig.baseUrl}/management/check-ins/${bookingId}/complete`,
      payload,
      { withCredentials: true }
    );
  }
}

export interface CheckInDetailDto {
  booking_id: string;
  prop_id: number;
  hotel_label: string;
  guest_name: string;
  guest_email: string;
  guest_phone: string;
  cedula: string;
  check_in_date: string;
  check_in_date_actual: string | null;
  check_in_time_actual: string | null;
  check_out_date: string;
  total_price: number | null;
  currency: string;
  total_nights: number;
  rooms: number;
  adults: number;
  children: number;
  status: string;
  stay_status: string;
  room_type_id: string;
  room_type_name: string;
  folio: string | null;
  check_in_by: string | null;
  payment_method: string;
  booking_source: string;
  comment: string;
  assigned_rooms: Array<{
    hotel_room_id: string;
    room_number: string;
    room_label: string;
    floor: string;
    room_status: string;
  }>;
  check_in_arrival_time: string;
  check_in_has_companions: boolean;
  check_in_companions_count: number;
  check_in_document_verified: boolean;
  check_in_keys_delivered: boolean;
  check_in_payment_pending: boolean;
  check_in_deposit_received: boolean;
  check_in_privacy_signed: boolean;
  check_in_observations: string;
}

export interface CheckInDetailSavePayload {
  check_in_arrival_time?: string;
  check_in_has_companions?: boolean;
  check_in_companions_count?: number;
  check_in_document_verified?: boolean;
  check_in_keys_delivered?: boolean;
  check_in_payment_pending?: boolean;
  check_in_deposit_received?: boolean;
  check_in_privacy_signed?: boolean;
  check_in_observations?: string;
}
