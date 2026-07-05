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
import type { RatePlanOption, ReservationCreateInput, ReservationCreateResult, ReservationStats } from '../models/reservations.model';
import type { ReceptionCalendarData, ReceptionCalendarReservation, ReceptionCalendarRoom } from '../models/reception-calendar.model';

/** Raw API response (snake_case) for reception calendar — rooms instead of types. */
interface ReceptionCalendarDto {
  rooms: Array<{
    room_number: string;
    hotel_room_id: string;
    room_type_name: string;
    room_type_id: string;
    reservations: Array<{
      booking_id: string;
      guest_name: string;
      adults: number;
      children: number;
      check_in_date: string;
      check_in_time: string;
      check_in_fraction: number;
      check_out_date: string;
      check_out_time: string;
      check_out_fraction: number;
      total_nights: number;
      status: string;
      visual_status: string;
      assigned_rooms: string[];
      hotel_room_id: string;
      room_number: string;
      total_price: number | null;
      currency: string;
    }>;
  }>;
  start_date: string;
  end_date: string;
  today: string;
}

function mapReceptionCalendar(dto: ReceptionCalendarDto): ReceptionCalendarData {
  return {
    rooms: dto.rooms.map(rm => ({
      roomNumber: rm.room_number,
      hotelRoomId: rm.hotel_room_id,
      roomTypeName: rm.room_type_name,
      roomTypeId: rm.room_type_id,
      reservations: rm.reservations.map(mapReceptionReservation),
    })),
    startDate: dto.start_date,
    endDate: dto.end_date,
    today: dto.today,
  };
}

function mapReceptionReservation(r: ReceptionCalendarDto['rooms'][number]['reservations'][number]): ReceptionCalendarReservation {
  return {
    bookingId: r.booking_id,
    guestName: r.guest_name,
    adults: r.adults,
    children: r.children,
    checkInDate: r.check_in_date,
    checkInTime: r.check_in_time,
    checkInFraction: r.check_in_fraction,
    checkOutDate: r.check_out_date,
    checkOutTime: r.check_out_time,
    checkOutFraction: r.check_out_fraction,
    totalNights: r.total_nights,
    status: r.status,
    visualStatus: r.visual_status as ReceptionCalendarReservation['visualStatus'],
    assignedRooms: r.assigned_rooms,
    hotelRoomId: r.hotel_room_id,
    roomNumber: r.room_number,
    totalPrice: r.total_price,
    currency: r.currency,
  };
}

@Injectable({
  providedIn: 'root'
})
export class ReservationsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getReservations(page: number, createdDate?: string, status?: string, propId?: number, folio?: string, stayStatus?: string, bookingSource?: string) {
    let params = new HttpParams().set('page', String(page));
    if (createdDate) {
      params = params.set('date', createdDate);
    }
    if (status) {
      params = params.set('status', status);
    }
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    if (folio) {
      params = params.set('folio', folio);
    }
    if (stayStatus) {
      params = params.set('stay_status', stayStatus);
    }
    if (bookingSource) {
      params = params.set('booking_source', bookingSource);
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
        room_status: string;
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

  /** Fetch reception calendar data — reservations grouped by room type for a property. */
  getReceptionCalendar(propId: number, startDate?: string, endDate?: string) {
    let params = new HttpParams().set('prop_id', String(propId));
    if (startDate) params = params.set('start_date', startDate);
    if (endDate) params = params.set('end_date', endDate);
    return this.http.get<ReceptionCalendarDto>(`${this.apiConfig.baseUrl}/management/reception/calendar`, {
      params,
      withCredentials: true,
    }).pipe(map(dto => mapReceptionCalendar(dto)));
  }

  /** Fetch available rate plans for a hotel + dates + optional room type */
  getAvailableRatePlans(propId: number, checkIn: string, checkOut: string, roomTypeId?: string) {
    let params = new HttpParams()
      .set('prop_id', String(propId))
      .set('check_in', checkIn)
      .set('check_out', checkOut);
    if (roomTypeId) {
      params = params.set('room_type_id', roomTypeId);
    }
    return this.http.get<{ rate_plans: any[] }>(
      `${this.apiConfig.baseUrl}/reservations/rate-plans`,
      { params, withCredentials: true }
    ).pipe(map(dto => ({
      rate_plans: (dto.rate_plans || []).map(p => ({
        ratePlanId: p.rate_plan_id,
        name: p.name,
        description: p.description,
        baseRate: p.base_rate,
        currency: p.currency,
        isActive: p.is_active,
        avgRatePerNight: p.avg_rate_per_night,
        totalPrice: p.total_price,
        nights: p.nights,
      })),
    })));
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
