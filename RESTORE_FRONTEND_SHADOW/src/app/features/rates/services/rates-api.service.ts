import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, switchMap, throwError } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import {
  buildCreateRateCalendarRequest,
  buildCreateRatePlanRequest,
  mapRatesResponse
} from '../mappers/rates.mapper';
import type {
  RatesOptionsResponseDto,
  RatesSnapshotResponseDto
} from '../models/rates.dto';

@Injectable({
  providedIn: 'root'
})
export class RatesApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getRates(propId: number) {
    const requestedParams = propId > 0 ? new HttpParams().set('prop_id', propId) : undefined;
    return this.http
      .get<RatesOptionsResponseDto>(`${this.apiConfig.baseUrl}/management/rates/options`, {
        params: requestedParams,
        withCredentials: true
      })
      .pipe(
        switchMap((options) => {
          const selectedPropId = options.selected_prop_id;
          if (!selectedPropId) {
            return throwError(() => new Error('No hay propiedades disponibles para tarifas.'));
          }

          return this.http
            .get<RatesSnapshotResponseDto>(`${this.apiConfig.baseUrl}/management/rates`, {
              params: new HttpParams().set('prop_id', selectedPropId),
              withCredentials: true
            })
            .pipe(map((snapshot) => mapRatesResponse(options, snapshot)));
        })
      );
  }

  createRatePlan(
    propId: number,
    value: {
      name: string;
      description: string;
      baseRate: number;
      currency: string;
      isActive: boolean;
    }
  ) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rates/plans`,
      buildCreateRatePlanRequest(propId, value),
      { withCredentials: true }
    );
  }

  createRateCalendarRow(
    propId: number,
    value: {
      ratePlanId: string;
      date: string;
      rateAmount: number;
      minStayNights: number;
      isClosed: boolean;
    }
  ) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rates/calendar`,
      buildCreateRateCalendarRequest(propId, value),
      { withCredentials: true }
    );
  }
}
