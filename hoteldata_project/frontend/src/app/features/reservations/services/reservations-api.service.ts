import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import {
  mapReservationCreatePayload,
  mapReservationCreateResult,
  mapReservationDetail,
  mapReservationOptions,
  mapReservationsList
} from '../mappers/reservations.mapper';
import type {
  ReservationCancelDto,
  ReservationCreateDto,
  ReservationDetailDto,
  ReservationOptionsDto,
  ReservationsListDto
} from '../models/reservations.dto';
import type { ReservationCreateInput } from '../models/reservations.model';

@Injectable({
  providedIn: 'root'
})
export class ReservationsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getReservations(page: number) {
    const params = new HttpParams().set('page', String(page));
    return this.http
      .get<ReservationsListDto>(`${this.apiConfig.baseUrl}/reservations`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapReservationsList(dto)));
  }

  getOptions() {
    return this.http
      .get<ReservationOptionsDto>(`${this.apiConfig.baseUrl}/reservations/options`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapReservationOptions(dto)));
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
}
