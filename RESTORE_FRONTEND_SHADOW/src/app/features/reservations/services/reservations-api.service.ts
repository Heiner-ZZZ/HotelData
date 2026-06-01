import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import {
  mapReservationDetailResponse,
  mapReservationListResponse,
  mapReservationOptionsResponse
} from '../mappers/reservations.mapper';
import type {
  ReservationCreateResponseDto,
  ReservationDetailResponseDto,
  ReservationListResponseDto,
  ReservationOptionsResponseDto
} from '../models/reservations.dto';

@Injectable({
  providedIn: 'root'
})
export class ReservationsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  listReservations(page: number) {
    return this.http
      .get<ReservationListResponseDto>(`${this.apiConfig.baseUrl}/reservations`, {
        params: new HttpParams().set('page', page),
        withCredentials: true
      })
      .pipe(map((dto) => mapReservationListResponse(dto)));
  }

  getReservationOptions(propId?: number) {
    let params = new HttpParams();
    if (propId) {
      params = params.set('prop_id', propId);
    }

    return this.http
      .get<ReservationOptionsResponseDto>(`${this.apiConfig.baseUrl}/reservations/options`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapReservationOptionsResponse(dto)));
  }

  createReservation(payload: Record<string, unknown>) {
    return this.http.post<ReservationCreateResponseDto>(
      `${this.apiConfig.baseUrl}/reservations`,
      payload,
      { withCredentials: true }
    );
  }

  getReservationDetail(bookingId: string) {
    return this.http
      .get<ReservationDetailResponseDto>(
        `${this.apiConfig.baseUrl}/reservations/${bookingId}`,
        { withCredentials: true }
      )
      .pipe(map((dto) => mapReservationDetailResponse(dto)));
  }

  cancelReservation(bookingId: string) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/reservations/${bookingId}/cancel`,
      {},
      { withCredentials: true }
    );
  }
}
