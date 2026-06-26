import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';

export interface DateHistoryEntry {
  date: string;
  count: number;
}
import {
  mapReservationCreatePayload,
  mapReservationCreateResult,
  mapReservationDetail,
  mapReservationOptions,
  mapReservationPreview,
  mapReservationStats,
  mapReservationsList
} from '../mappers/reservations.mapper';
import type {
  ReservationCancelDto,
  ReservationConfirmRejectDto,
  ReservationCreateDto,
  ReservationDetailDto,
  ReservationOptionsDto,
  ReservationPreviewDto,
  ReservationStatsDto,
  ReservationsListDto
} from '../models/reservations.dto';
import type { ReservationCreateInput, ReservationCreateResult, ReservationStats } from '../models/reservations.model';

@Injectable({
  providedIn: 'root'
})
export class ReservationsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getReservations(page: number, createdDate?: string, status?: string) {
    let params = new HttpParams().set('page', String(page));
    if (createdDate) {
      params = params.set('date', createdDate);
    }
    if (status) {
      params = params.set('status', status);
    }
    return this.http
      .get<ReservationsListDto>(`${this.apiConfig.baseUrl}/reservations`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapReservationsList(dto)));
  }

  getReservationDates(propId?: number) {
    let params = new HttpParams();
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http.get<DateHistoryEntry[]>(`${this.apiConfig.baseUrl}/reservations/dates`, {
      params,
      withCredentials: true
    });
  }

  getOptions() {
    return this.http
      .get<ReservationOptionsDto>(`${this.apiConfig.baseUrl}/reservations/options`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapReservationOptions(dto)));
  }

  previewReservation(input: ReservationCreateInput) {
    return this.http
      .post<ReservationPreviewDto>(
        `${this.apiConfig.baseUrl}/reservations/preview`,
        mapReservationCreatePayload(input),
        { withCredentials: true }
      )
      .pipe(map((dto) => mapReservationPreview(dto)));
  }

  createReservation(input: ReservationCreateInput) {
    return this.http
      .post<ReservationCreateDto>(
        `${this.apiConfig.baseUrl}/reservations`,
        mapReservationCreatePayload(input),
        { withCredentials: true }
      )
      .pipe(map((dto) => mapReservationCreateResult(dto) as ReservationCreateResult));
  }

  getReservationDetail(bookingId: string) {
    return this.http
      .get<ReservationDetailDto>(`${this.apiConfig.baseUrl}/reservations/${bookingId}`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapReservationDetail(dto)));
  }

  cancelReservation(bookingId: string) {
    return this.http.post<ReservationCancelDto>(
      `${this.apiConfig.baseUrl}/reservations/${bookingId}/cancel`,
      {},
      { withCredentials: true }
    );
  }

  getStats() {
    return this.http
      .get<ReservationStatsDto>(`${this.apiConfig.baseUrl}/reservations/stats`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapReservationStats(dto)));
  }

  exportCsv() {
    return this.http.get(`${this.apiConfig.baseUrl}/reservations/export?format=csv`, {
      withCredentials: true,
      responseType: 'blob'
    });
  }

  confirmReservation(bookingId: string) {
    return this.http.post<ReservationConfirmRejectDto>(
      `${this.apiConfig.baseUrl}/reservations/${bookingId}/confirm`,
      {},
      { withCredentials: true }
    );
  }

  rejectReservation(bookingId: string) {
    return this.http.post<ReservationConfirmRejectDto>(
      `${this.apiConfig.baseUrl}/reservations/${bookingId}/reject`,
      {},
      { withCredentials: true }
    );
  }

  modifyBooking(bookingId: string, payload: Record<string, unknown>) {
    return this.http.patch<ReservationConfirmRejectDto>(
      `${this.apiConfig.baseUrl}/reservations/${bookingId}`,
      payload,
      { withCredentials: true }
    );
  }

  getRoomGuests(bookingId: string) {
    return this.http.get<Record<string, unknown>[]>(
      `${this.apiConfig.baseUrl}/reservations/${bookingId}/room-guests`,
      { withCredentials: true }
    );
  }

  saveRoomGuests(bookingId: string, roomGuests: { room_index: number; guests: Record<string, unknown>[] }[]) {
    return this.http.put<Record<string, unknown>[]>(
      `${this.apiConfig.baseUrl}/reservations/${bookingId}/room-guests`,
      { room_guests: roomGuests },
      { withCredentials: true }
    );
  }

  getCheckInStatus(bookingId: string) {
    return this.http.get<Record<string, unknown>>(
      `${this.apiConfig.baseUrl}/reservations/${bookingId}/check-in-status`,
      { withCredentials: true }
    );
  }

  validateCoupon(couponCode: string, propId: number) {
    return this.http.post<{valid: boolean; message: string; discount_percent: number}>(
      `${this.apiConfig.baseUrl}/reservations/validate-coupon`,
      { coupon_code: couponCode, prop_id: propId },
      { withCredentials: true }
    );
  }

  createGuestReview(bookingId: string, propId: number, rating: number, title: string, comment: string) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/reviews/guest`,
      { booking_id: bookingId, prop_id: propId, rating, title, comment },
      { withCredentials: true }
    );
  }

  /** Get available physical rooms for a booking */
  getAvailableRooms(bookingId: string) {
    return this.http.get<{
      prop_id: number;
      room_type: { name: string; base_capacity: number; max_adults: number } | null;
      rooms_required: number;
      rooms_available: number;
      available_rooms: Array<{
        hotel_room_id: string;
        room_number: string;
        room_label: string;
        floor: string;
      }>;
      assigned_rooms: string[];
    }>(`${this.apiConfig.baseUrl}/management/bookings/${bookingId}/available-rooms`, {
      withCredentials: true,
    });
  }

  /** Assign physical rooms to a booking */
  assignRooms(bookingId: string, roomIds: string[]) {
    return this.http.post<{ booking_id: string; assigned_rooms: string[]; assigned_count: number }>(
      `${this.apiConfig.baseUrl}/management/bookings/${bookingId}/assign-rooms`,
      { room_ids: roomIds },
      { withCredentials: true }
    );
  }

  /** Search registered users by name or email for quick guest data prefill */
  searchUsers(q: string) {
    const params = new HttpParams().set('q', q).set('limit', '10');
    return this.http.get<{ items: Array<{ name: string; email: string; phone: string; cedula: string }> }>(
      `${this.apiConfig.baseUrl}/management/users/search`,
      { params, withCredentials: true }
    );
  }

  /** Check if a hotel has inventory/availability for a given date range */
  getHotelAvailability(propId: number, checkIn: string, checkOut: string) {
    const params = new HttpParams()
      .set('prop_id', String(propId))
      .set('check_in', checkIn)
      .set('check_out', checkOut);
    return this.http.get<{
      hasInventory: boolean;
      hasRoomTypes: boolean;
      totalRooms: number;
      availableRooms: number;
      message: string;
    }>(`${this.apiConfig.baseUrl}/reservations/availability-check`, {
      params,
      withCredentials: true,
    });
  }
}
