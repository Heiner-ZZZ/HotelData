import { HttpClient, HttpContext, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';

import { PropertyContextService } from '../../../shared/services/property-context.service';

export interface DateHistoryEntry {
  date: string;
  count: number;
}

/** Fila cruda (snake_case) de una reserva sin precio (banner del admin). */
export interface UnpricedBookingRaw {
  booking_id: string;
  prop_id: number;
  status: string;
  guest_name?: string;
  check_in_date?: string;
  check_out_date?: string;
  total_nights?: number;
  currency?: string;
  created_at?: string;
}

export interface UnpricedBooking {
  bookingId: string;
  propId: number;
  status: string;
  guestName: string;
  checkInDate: string;
  checkOutDate: string;
  totalNights: number;
  currency: string;
}

/** Resultado de POST /reservations/{booking_id}/recalculate-price. */
export interface RecalculatePriceResult {
  booking_id: string;
  total_price: number | null;
  status: string;
  currency?: string;
  already_priced?: boolean;
  skipped?: string | null;
  penalty_recomputed?: boolean;
  folio_recomputed?: boolean;
}

export function mapUnpriced(raw: UnpricedBookingRaw): UnpricedBooking {
  return {
    bookingId: raw.booking_id,
    propId: raw.prop_id,
    status: raw.status,
    guestName: raw.guest_name || '',
    checkInDate: raw.check_in_date || '',
    checkOutDate: raw.check_out_date || '',
    totalNights: raw.total_nights || 0,
    currency: raw.currency || 'USD',
  };
}

/** Raw rate-plan row returned by `GET /reservations/rate-plans`. */
interface RatePlanRaw {
  rate_plan_id: string;
  name: string;
  description: string;
  base_rate: number;
  currency: string;
  is_active: boolean;
  avg_rate_per_night: number;
  total_price: number;
  nights: number;
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
  CancelPreviewDto,
  ReservationCancelDto,
  ReservationConfirmRejectDto,
  ReservationCreateDto,
  ReservationDetailDto,
  ReservationOptionsDto,
  ReservationPreviewDto,
  ReservationStatsDto,
  ReservationsListDto
} from '../models/reservations.dto';
import type { ReservationCreateInput, ReservationCreateResult } from '../models/reservations.model';
import type { ReceptionCalendarData, ReceptionCalendarReservation } from '../models/reception-calendar.model';

/** Raw API response (snake_case) for reception calendar — rooms instead of types. */
export interface ReceptionCalendarDto {
  rooms: {
    room_number: string;
    hotel_room_id: string;
    room_type_name: string;
    room_type_id: string;
    floor: string;
    reservations: {
      booking_id: string;
      guest_name: string;
      adults: number;
      children: number;
      check_in_date: string;
      check_in_time: string;
      estimated_arrival_time: string;
      late_checkin: boolean;
      check_out_date: string;
      check_out_time: string;
      total_nights: number;
      status: string;
      stay_status?: string | null;
      visual_status: string;
      reopen_window?: 'open' | 'too_late' | 'stay_ended' | null;
      assigned_rooms: string[];
      hotel_room_id: string;
      room_number: string;
      total_price: number | null;
      currency: string;
    }[];
  }[];
  start_date: string;
  end_date: string;
  today: string;
  /** Hotel-wide policy defaults (HH:MM) used to prefill a new reservation. */
  check_in_time?: string;
  check_out_time?: string;
}

export function mapReceptionCalendar(dto: ReceptionCalendarDto): ReceptionCalendarData {
  return {
    rooms: dto.rooms.map(rm => ({
      roomNumber: rm.room_number,
      hotelRoomId: rm.hotel_room_id,
      roomTypeName: rm.room_type_name,
      roomTypeId: rm.room_type_id,
      floor: rm.floor || '',
      reservations: rm.reservations.map(mapReceptionReservation),
    })),
    startDate: dto.start_date,
    endDate: dto.end_date,
    today: dto.today,
    checkInTime: dto.check_in_time || '',
    checkOutTime: dto.check_out_time || '',
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
    estimatedArrivalTime: r.estimated_arrival_time || '',
    lateCheckin: !!r.late_checkin,
    checkOutDate: r.check_out_date,
    checkOutTime: r.check_out_time,
    totalNights: r.total_nights,
    status: r.status,
    stayStatus: r.stay_status || '',
    visualStatus: r.visual_status as ReceptionCalendarReservation['visualStatus'],
    reopenWindow: (r.reopen_window as ReceptionCalendarReservation['reopenWindow']) ?? null,
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
  private readonly propertyCtx = inject(PropertyContextService);

  private propParams(): HttpParams {
    const ctxPid = this.propertyCtx.currentPropId();
    if (ctxPid > 0) return new HttpParams().set('prop_id', String(ctxPid));
    try {
      const raw = new URLSearchParams(window.location.search).get('prop_id');
      const urlPid = raw ? Number(raw) : 0;
      if (urlPid > 0) return new HttpParams().set('prop_id', String(urlPid));
    } catch {
      // ignora
    }
    return new HttpParams();
  }

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
      .get<ReservationsListDto>('/reservations', { params })
      .pipe(map((dto) => mapReservationsList(dto)));
  }

  getReservationDates(propId?: number) {
    let params = new HttpParams();
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http.get<DateHistoryEntry[]>('/reservations/dates', { params });
  }

  getOptions() {
    return this.http
      .get<ReservationOptionsDto>('/reservations/options')
      .pipe(map((dto) => mapReservationOptions(dto)));
  }

  previewReservation(input: ReservationCreateInput) {
    return this.http
      .post<ReservationPreviewDto>(
        '/reservations/preview',
        mapReservationCreatePayload(input),
      )
      .pipe(map((dto) => mapReservationPreview(dto)));
  }

  createReservation(input: ReservationCreateInput) {
    return this.http
      .post<ReservationCreateDto>(
        '/reservations',
        mapReservationCreatePayload(input),
      )
      .pipe(map((dto) => mapReservationCreateResult(dto) as ReservationCreateResult));
  }

  getReservationDetail(bookingId: string) {
    return this.http
      .get<ReservationDetailDto>(`/reservations/${bookingId}`, { params: this.propParams() })
      .pipe(map((dto) => mapReservationDetail(dto)));
  }

  /** Flip one checklist item's fulfillment status (pending ↔ fulfilled). */
  updateSpecialRequestStatus(bookingId: string, label: string, status: 'pending' | 'fulfilled', kind: 'special_request' | 'amenity' = 'special_request') {
    return this.http.patch<{ ok: boolean; kind: string; fulfillment: { label: string; status: string; fulfilled_at?: string | null }[] }>(
      `/reservations/${bookingId}/special-requests`,
      { kind, label, status },
      { params: this.propParams() },
    );
  }

  getCancelPreview(bookingId: string): Observable<CancelPreviewDto> {
    return this.http.get<CancelPreviewDto>(`/reservations/${bookingId}/cancel-preview`, { params: this.propParams() });
  }

  cancelReservation(bookingId: string) {
    return this.http.post<ReservationCancelDto>(
      `/reservations/${bookingId}/cancel`,
      {},
      { params: this.propParams() },
    );
  }

  getStats() {
    return this.http
      .get<ReservationStatsDto>('/reservations/stats')
      .pipe(map((dto) => mapReservationStats(dto)));
  }

  /** Bookings sin ``total_price`` (banner 'Recalcular precio' — solo staff). */
  getUnpricedReservations() {
    return this.http
      .get<{ items: UnpricedBookingRaw[]; total: number }>('/reservations/unpriced')
      .pipe(map((dto) => dto.items.map(mapUnpriced)));
  }

  /**
   * Recalcula el precio de una reserva sin precio — MISMO path canónico que
   * el script ``migrate_backfill_booking_prices.py`` (fallback a
   * ``rate_plans.base_rate`` + penalizaciones + folio).
   */
  recalculatePrice(bookingId: string) {
    return this.http.post<RecalculatePriceResult>(
      `/reservations/${bookingId}/recalculate-price`,
      {},
      { params: this.propParams() },
    );
  }

  exportCsv() {
    return this.http.get('/reservations/export', {
      responseType: 'blob',
      params: this.propParams().set('format', 'csv'),
    });
  }

  confirmReservation(bookingId: string, context?: HttpContext) {
    return this.http.post<ReservationConfirmRejectDto>(
      `/reservations/${bookingId}/confirm`,
      {},
      { params: this.propParams(), ...(context ? { context } : {}) },
    );
  }

  rejectReservation(bookingId: string, context?: HttpContext) {
    return this.http.post<ReservationConfirmRejectDto>(
      `/reservations/${bookingId}/reject`,
      {},
      { params: this.propParams(), ...(context ? { context } : {}) },
    );
  }

  modifyBooking(bookingId: string, payload: Record<string, unknown>) {
    return this.http.patch<ReservationConfirmRejectDto>(
      `/reservations/${bookingId}`,
      payload,
      { params: this.propParams() },
    );
  }

  getRoomGuests(bookingId: string) {
    return this.http.get<Record<string, unknown>[]>(
      `/reservations/${bookingId}/room-guests`,
      { params: this.propParams() },
    );
  }

  saveRoomGuests(bookingId: string, roomGuests: { room_index: number; guests: Record<string, unknown>[] }[]) {
    return this.http.put<Record<string, unknown>[]>(
      `/reservations/${bookingId}/room-guests`,
      { room_guests: roomGuests },
      { params: this.propParams() },
    );
  }

  getCheckInStatus(bookingId: string) {
    return this.http.get<Record<string, unknown>>(
      `/reservations/${bookingId}/check-in-status`,
      { params: this.propParams() },
    );
  }

  validateCoupon(couponCode: string, propId: number, extra?: { checkIn?: string; checkOut?: string; ratePlanId?: string; roomTypeId?: string }) {
    return this.http.post<{valid: boolean; message: string; discount_percent: number}>(
      '/reservations/validate-coupon',
      {
        coupon_code: couponCode,
        prop_id: propId,
        check_in: extra?.checkIn,
        check_out: extra?.checkOut,
        rate_plan_id: extra?.ratePlanId,
        room_type_id: extra?.roomTypeId,
      },
    );
  }

  createGuestReview(bookingId: string, propId: number, rating: number, title: string, comment: string) {
    return this.http.post(
      '/reviews/guest',
      { booking_id: bookingId, prop_id: propId, rating, title, comment },
    );
  }

  /** Get available physical rooms for a booking */
  getAvailableRooms(bookingId: string) {
    return this.http.get<{
      prop_id: number;
      room_type: { name: string; base_capacity: number; max_adults: number } | null;
      rooms_required: number;
      rooms_available: number;
      available_rooms: {
        hotel_room_id: string;
        room_number: string;
        room_label: string;
        floor: string;
        room_status: string;
      }[];
      assigned_rooms: string[];
    }>(`/management/bookings/${bookingId}/available-rooms`, { params: this.propParams() });
  }

  /** Assign physical rooms to a booking */
  assignRooms(bookingId: string, roomIds: string[]) {
    return this.http.post<{ booking_id: string; assigned_rooms: string[]; assigned_count: number }>(
      `/management/bookings/${bookingId}/assign-rooms`,
      { room_ids: roomIds },
      { params: this.propParams() },
    );
  }

  /** Search registered users by name or email for quick guest data prefill */
  searchUsers(q: string) {
    const params = this.propParams().set('q', q).set('limit', '10');
    return this.http.get<{ items: { name: string; email: string; phone: string; cedula: string }[] }>(
      '/management/users/search',
      { params },
    );
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
    return this.http.get<{ rate_plans: RatePlanRaw[] }>(
      '/reservations/rate-plans',
      { params },
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
    }>('/reservations/availability-check', { params });
  }
}

