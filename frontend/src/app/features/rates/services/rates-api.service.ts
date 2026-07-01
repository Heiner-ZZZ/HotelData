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
    roomTypeId?: string;
    isActive: boolean;
    eligibleRoles?: string[];
  }) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rates/plans`,
      {
        prop_id: payload.propId,
        name: payload.name,
        description: payload.description,
        base_rate: payload.baseRate,
        currency: payload.currency,
        room_type_id: payload.roomTypeId || '',
        is_active: payload.isActive,
        eligible_roles: payload.eligibleRoles ?? []
      },
      { withCredentials: true }
    );
  }

  updateRatePlan(planId: string, payload: {
    name: string;
    description: string;
    baseRate: number;
    currency: string;
    roomTypeId?: string;
    isActive: boolean;
    eligibleRoles?: string[];
  }) {
    return this.http.put(
      `${this.apiConfig.baseUrl}/management/rates/plans/${planId}`,
      {
        name: payload.name,
        description: payload.description,
        base_rate: payload.baseRate,
        currency: payload.currency,
        room_type_id: payload.roomTypeId || '',
        is_active: payload.isActive,
        eligible_roles: payload.eligibleRoles ?? []
      },
      { withCredentials: true }
    );
  }

  deleteRatePlan(planId: string) {
    return this.http.delete(
      `${this.apiConfig.baseUrl}/management/rates/plans/${planId}`,
      { withCredentials: true }
    );
  }

  createSeasonalRule(payload: {
    propId: number;
    ratePlanId: string;
    name: string;
    startDate: string;
    endDate: string;
    priceOverride: number;
  }) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rates/seasonal-rules`,
      {
        prop_id: payload.propId,
        rate_plan_id: payload.ratePlanId,
        name: payload.name,
        start_date: payload.startDate,
        end_date: payload.endDate,
        price_override: payload.priceOverride
      },
      { withCredentials: true }
    );
  }

  updateSeasonalRule(ruleId: string, payload: {
    ratePlanId: string;
    name: string;
    startDate: string;
    endDate: string;
    priceOverride: number;
  }) {
    return this.http.put(
      `${this.apiConfig.baseUrl}/management/rates/seasonal-rules/${ruleId}`,
      {
        rate_plan_id: payload.ratePlanId,
        name: payload.name,
        start_date: payload.startDate,
        end_date: payload.endDate,
        price_override: payload.priceOverride
      },
      { withCredentials: true }
    );
  }

  deleteSeasonalRule(ruleId: string) {
    return this.http.delete(
      `${this.apiConfig.baseUrl}/management/rates/seasonal-rules/${ruleId}`,
      { withCredentials: true }
    );
  }

  batchUpdateCalendar(payload: {
    propId: number;
    ratePlanId: string;
    startDate: string;
    endDate: string;
    rateAmount: number;
    minStayNights?: number;
    isClosed?: boolean;
    onlyWeekends?: boolean;
  }) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rates/calendar/batch`,
      {
        prop_id: payload.propId,
        rate_plan_id: payload.ratePlanId,
        start_date: payload.startDate,
        end_date: payload.endDate,
        rate_amount: payload.rateAmount,
        min_stay_nights: payload.minStayNights,
        is_closed: payload.isClosed,
        only_weekends: payload.onlyWeekends || false
      },
      { withCredentials: true }
    );
  }

  generateCalendar(payload: {
    propId: number;
    ratePlanId?: string;
    startDate?: string;
    endDate?: string;
  }) {
    return this.http.post<{ plans_processed: number; entries_generated: number; start_date: string; end_date: string }>(
      `${this.apiConfig.baseUrl}/management/rates/calendar/generate`,
      {
        prop_id: payload.propId,
        rate_plan_id: payload.ratePlanId || '',
        start_date: payload.startDate || '',
        end_date: payload.endDate || '',
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
    couponCount: number;
    couponCode: string;
    isActive: boolean;
  }) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/promotions`,
      {
        prop_id: payload.propId,
        name: payload.name,
        description: payload.description,
        discount_percent: payload.discountPercent,
        start_date: payload.startDate,
        end_date: payload.endDate,
        coupon_count: payload.couponCount,
        coupon_code: payload.couponCode,
        is_active: payload.isActive
      },
      { withCredentials: true }
    );
  }

  updatePromotion(campaignId: string, payload: {
    name?: string;
    description?: string;
    discountPercent?: number;
    couponCount?: number;
    startDate?: string;
    endDate?: string;
    isActive?: boolean;
  }) {
    return this.http.put(
      `${this.apiConfig.baseUrl}/management/promotions/${campaignId}`,
      {
        name: payload.name,
        description: payload.description,
        discount_percent: payload.discountPercent,
        coupon_count: payload.couponCount,
        start_date: payload.startDate,
        end_date: payload.endDate,
        is_active: payload.isActive
      },
      { withCredentials: true }
    );
  }

  togglePromotion(campaignId: string) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/promotions/${campaignId}/toggle`,
      {},
      { withCredentials: true }
    );
  }

  listPropertyPromotions(propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.get<{ campaigns: Array<{
      campaign_id: string;
      name: string;
      description?: string;
      discount_percent?: number;
      start_date?: string;
      end_date?: string;
      is_active: boolean;
      coupon_total?: number;
      coupon_used?: number;
      coupon_available?: number;
      discount_percent_label?: string;
      hotel_label?: string;
    }>; total: number }>(
      `${this.apiConfig.baseUrl}/management/promotions`,
      { params, withCredentials: true }
    );
  }
}
