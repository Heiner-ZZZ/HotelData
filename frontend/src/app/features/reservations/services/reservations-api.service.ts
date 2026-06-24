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
import type { ReservationCreateInput, ReservationStats } from '../models/reservations.model';

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
      .pipe(map((dto) => mapReservationCreateResult(dto)));
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
}
