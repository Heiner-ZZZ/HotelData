import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { catchAuthError } from '../../../shared/utils/catch-auth-error';

export interface DateHistoryEntry {
  date: string;
  count: number;
  prop_id?: number;
  hotel_label?: string;
}

@Injectable({ providedIn: 'root' })
export class CheckInsApiService {
  private readonly http = inject(HttpClient);

  getCheckInDates(propId?: number) {
    let params = new HttpParams();
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http.get<DateHistoryEntry[]>('/management/check-ins/dates', { params })
      .pipe(catchAuthError());
  }

  completeCheckIn(bookingId: string) {
    return this.http.post(`/management/check-ins/${bookingId}/complete`, {});
  }

  /** Update check-in date/time using the shared PATCH /api/reservations/{id} endpoint */
  updateCheckInDateTime(bookingId: string, checkInDate?: string, checkInTime?: string) {
    const payload: Record<string, string> = {};
    if (checkInDate !== undefined) payload['check_in_date'] = checkInDate;
    if (checkInTime !== undefined) payload['check_in_time'] = checkInTime;
    return this.http.patch<{ booking_id: string; updated: boolean }>(
      `/reservations/${bookingId}`,
      payload,
    );
  }

  /** ═══ Check-In Detail Page ═══ */

  /** Fetch all check-in detail data for the detailed check-in page. */
  getCheckInDetail(bookingId: string) {
    return this.http.get<CheckInDetailDto>(
      `/management/check-ins/${bookingId}/detail`,
    );
  }

  /** Save check-in detail fields incrementally (draft). */
  saveCheckInDetail(bookingId: string, payload: Partial<CheckInDetailSavePayload>) {
    return this.http.patch<{ booking_id: string; updated: boolean; fields_updated: string[] }>(
      `/management/check-ins/${bookingId}/detail`,
      payload,
    );
  }

  /** Complete check-in with all detail data. */
  completeCheckInWithDetail(bookingId: string, payload: Partial<CheckInDetailSavePayload> & { payment_method?: string }) {
    return this.http.post<{ booking_id: string; stay_status: string; folio?: string; invoice_id?: string }>(
      `/management/check-ins/${bookingId}/complete`,
      payload,
    ).pipe(catchAuthError());
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
  assigned_rooms: {
    hotel_room_id: string;
    room_number: string;
    room_label: string;
    floor: string;
    room_status: string;
  }[];
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
