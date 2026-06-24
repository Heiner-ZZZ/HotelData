import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapRatePlanOptions, mapRatesPropertyOptions, mapRatesResponse } from '../mappers/rates.mapper';
import type { PropertyOptionsPage } from '../models/rates.model';
import type { RatesDto, RatesOptionsDto } from '../models/rates.dto';

@Injectable({
  providedIn: 'root'
})
export class RatesApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getRates(propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http
      .get<RatesDto>(`${this.apiConfig.baseUrl}/management/rates`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapRatesResponse(dto)));
  }

  getPropertyOptions(q = '', page = 1, pageSize = 10) {
    const params = new HttpParams()
      .set('q', q)
      .set('page', String(page))
      .set('page_size', String(pageSize));
    return this.http
      .get<RatesOptionsDto>(`${this.apiConfig.baseUrl}/management/rates/options`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapRatesPropertyOptions(dto) as PropertyOptionsPage));
  }

  getRatePlanOptions(propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http
      .get<RatesOptionsDto>(`${this.apiConfig.baseUrl}/management/rates/options`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapRatePlanOptions(dto)));
  }

  createRatePlan(payload: {
    propId: number;
    name: string;
    description: string;
    baseRate: number;
    currency: string;
    isActive: boolean;
  }) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rates/plans`,
      {
        prop_id: payload.propId,
        name: payload.name,
        description: payload.description,
        base_rate: payload.baseRate,
        currency: payload.currency,
        is_active: payload.isActive
      },
      { withCredentials: true }
    );
  }

  saveRate(payload: {
    propId: number;
    ratePlanId: string;
    date: string;
    rateAmount: number;
    minStayNights: number;
    isClosed: boolean;
  }) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rates/calendar`,
      {
        prop_id: payload.propId,
        rate_plan_id: payload.ratePlanId,
        date: payload.date,
        rate_amount: payload.rateAmount,
        min_stay_nights: payload.minStayNights,
        is_closed: payload.isClosed
      },
      { withCredentials: true }
    );
  }

  createPromotion(payload: {
    propId: number;
    name: string;
    description: string;
    discountPercent: number;
    startDate: string;
    endDate: string;
    couponCode: string;
    isActive: boolean;
  }) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rates/promotions`,
      {
        prop_id: payload.propId,
        name: payload.name,
        description: payload.description,
        discount_percent: payload.discountPercent,
        start_date: payload.startDate,
        end_date: payload.endDate,
        coupon_code: payload.couponCode,
        is_active: payload.isActive
      },
      { withCredentials: true }
    );
  }
}
