import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { catchAuthError } from '../../../shared/utils/catch-auth-error';
import { PropertyContextService } from '../../../shared/services/property-context.service';

export interface DateHistoryEntry {
  date: string;
  count: number;
  prop_id?: number;
  hotel_label?: string;
}

@Injectable({ providedIn: 'root' })
export class CheckInsApiService {
  private readonly http = inject(HttpClient);
  private readonly propertyCtx = inject(PropertyContextService);

  private propParams(propId?: number): HttpParams {
    if (propId && propId > 0) return new HttpParams().set('prop_id', String(propId));
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

  getCheckInDates(propId?: number) {
    let params = new HttpParams();
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http.get<DateHistoryEntry[]>('/management/check-ins/dates', { params })
      .pipe(catchAuthError());
  }

  /**
   * Check-in rápido desde el listado: flujo express que omite el checklist
   * manual (llaves/documento) por diseño — se completa después en el detalle
   * vía PATCH. Sin express:true el endpoint responde 422 (regla alineada
   * manual vs masivo).
   */
  completeCheckIn(bookingId: string) {
    return this.http.post(`/management/check-ins/${bookingId}/complete`, { express: true }, { params: this.propParams() });
  }

  /** Update check-in date/time using the shared PATCH /api/reservations/{id} endpoint */
  updateCheckInDateTime(bookingId: string, checkInDate?: string, checkInTime?: string) {
    const payload: Record<string, string> = {};
    if (checkInDate !== undefined) payload['check_in_date'] = checkInDate;
    if (checkInTime !== undefined) payload['check_in_time'] = checkInTime;
    return this.http.patch<{ booking_id: string; updated: boolean }>(
      `/reservations/${bookingId}`,
      payload,
      { params: this.propParams() },
    );
  }

  /** ═══ Check-In Detail Page ═══ */

  /** Fetch all check-in detail data for the detailed check-in page. */
  getCheckInDetail(bookingId: string) {
    return this.http.get<CheckInDetailDto>(
      `/management/check-ins/${bookingId}/detail`,
      { params: this.propParams() },
    );
  }

  /** Save check-in detail fields incrementally (draft). */
  saveCheckInDetail(bookingId: string, payload: Partial<CheckInDetailSavePayload>) {
    return this.http.patch<{ booking_id: string; updated: boolean; fields_updated: string[] }>(
      `/management/check-ins/${bookingId}/detail`,
      payload,
      { params: this.propParams() },
    );
  }

  /** Complete check-in with all detail data. */
  completeCheckInWithDetail(
    bookingId: string,
    payload: Partial<CheckInDetailSavePayload> & EarlyCheckInSavePayload & { payment_method?: string },
  ) {
    return this.http.post<{
      booking_id: string;
      stay_status: string;
      folio?: string;
      invoice_id?: string;
      check_in_mode?: string;
      early_check_in_fee?: number;
    }>(
      `/management/check-ins/${bookingId}/complete`,
      payload,
      { params: this.propParams() },
    ).pipe(catchAuthError());
  }

  /**
   * Validate real-time room availability for early check-in authorization.
   * Returns current room status, overlapping reservations, and pending tasks.
   */
  validateRoomAvailability(bookingId: string) {
    return this.http.get<RoomAvailabilityDto>(
      `/management/check-ins/${bookingId}/room-availability`,
      { params: this.propParams() },
    ).pipe(catchAuthError());
  }

  /**
   * Recepción declara (o retira) una llegada tardía para una reserva.
   * El flag protege la reserva del auto no-show; no modifica fechas.
   */
  declareLateArrival(
    bookingId: string,
    payload: { declared_late_arrival: boolean; estimated_arrival_time?: string },
  ) {
    return this.http.post<{
      booking_id: string;
      declared_late_arrival: boolean;
      estimated_arrival_time: string;
    }>(
      `/management/check-ins/${bookingId}/declare-late-arrival`,
      payload,
      { params: this.propParams() },
    ).pipe(catchAuthError());
  }

  /**
   * Reabre una reserva cerrada como no-show (autorización de gerente).
   * La reserva vuelve a pending y el folio de penalización se retira:
   * si solo contenía la penalización se elimina (``folio_deleted``); si
   * arrastra pagos u otros cargos, la penalización se revierte y el folio
   * se conserva para gestionarlo en Facturación (``reversal_amount``).
   */
  reopenNoShow(bookingId: string, reason: string, propId?: number) {
    return this.http.post<{
      ok: boolean;
      booking_id: string;
      stay_status: string;
      penalty_amount: number;
      folio_number: string | null;
      /** True cuando la penalización fue retirada (folio eliminado o cargo revertido). */
      penalty_removed: boolean;
      /** True solo cuando el folio penalty-only fue eliminado por completo. */
      folio_deleted?: boolean;
      /** Monto revertido cuando el folio se conservó (crédito a favor del huésped). */
      reversal_amount?: number;
    }>(
      `/management/bookings/${bookingId}/reopen-no-show`,
      { reason },
      { params: this.propParams(propId) },
    ).pipe(catchAuthError());
  }

}

export interface EarlyCheckInDto {
  enabled: boolean;
  is_early: boolean;
  minutes_before: number;
  courtesy_minutes: number;
  requires_approval: boolean;
  check_in_time: string;
  default_fee: number;
  recorded_mode?: string;
  recorded_minutes?: number;
  recorded_fee?: number;
  approved_by?: string;
  reason?: string;
  /** Hora local persistida cuando se completó el early check-in. */
  actual_date?: string | null;
  actual_time?: string | null;
}

export interface EarlyCheckInSavePayload {
  early_check_in_mode?: 'early_courtesy' | 'early_approved';
  early_check_in_approved?: boolean;
  early_check_in_reason?: string;
  early_check_in_fee?: number;
}

export interface RoomAvailabilityDto {
  booking_id: string;
  all_available: boolean;
  rooms: {
    hotel_room_id: string;
    room_label: string;
    floor: string;
    status: string;
    is_vacant: boolean;
    available: boolean;
    overlapping_bookings?: {
      booking_id: string;
      guest_name: string;
      check_in_date: string;
      check_out_date: string;
      stay_status: string;
    }[];
    pending_tasks?: string[];
  }[];
  issues: string[];
  validated_at: string;
}

export interface LateArrivalDto {
  guaranteed_reservation: boolean;
  late_arrival_cutoff: string;
  no_show_execution: 'next_day' | 'same_day_cutoff' | 'manual';
  declared_late_arrival: boolean;
  protected_from_auto_no_show: boolean;
  is_late_arrival_window: boolean;
  check_in_days_ago: number | null;
  blocked_reason: 'no_show' | 'stay_ended' | 'too_late' | null;
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
  /** Hora estimada de llegada declarada por el huésped (HH:MM). */
  estimated_arrival_time: string;
  /** Marcador de late check-in (llegada tarde). */
  late_checkin: boolean;
  early_check_in?: EarlyCheckInDto;
  /** Contexto de llegada tardía / no-show (política hotel + ventana). */
  late_arrival?: LateArrivalDto;
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
  no_show_penalty_amount: number | null;
  /** Marca de reapertura de no-show: el gerente reabrió porque el huésped llegó. */
  no_show_reopened_at: string | null;
  no_show_reopened_by: string;
  no_show_reopen_reason: string;
  no_show_penalty_removed: boolean;
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
