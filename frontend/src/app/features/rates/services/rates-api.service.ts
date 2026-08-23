import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapRatePlanOptions, mapRatesPropertyOptions, mapRatesResponse } from '../mappers/rates.mapper';
import { mapRoomPerformanceDashboard } from '../mappers/room-performance.mapper';
import { mapRateCalendarDashboard } from '../mappers/rate-calendar.mapper';
import type { PropertyOptionsPage } from '../models/rates.model';
import type { RatesDto, RatesOptionsDto } from '../models/rates.dto';
import type { RoomPerformanceDashboardDto } from '../models/room-performance.dto';
import type { RateCalendarDashboardDto } from '../models/rate-calendar.dto';

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

  /** Tactical R1.2 dashboard: ADR por fecha, tipo de habitación y canal (ClickHouse). */
  getRoomPerformanceDashboard(params: {
    prop_id?: number;
    date_from?: string;
    date_to?: string;
    room_type_id?: string;
    channel?: string;
    page?: number;
    page_size?: number;
  }) {
    let hp = new HttpParams();
    if (params.prop_id) hp = hp.set('prop_id', String(params.prop_id));
    if (params.date_from) hp = hp.set('date_from', params.date_from);
    if (params.date_to) hp = hp.set('date_to', params.date_to);
    if (params.room_type_id) hp = hp.set('room_type_id', params.room_type_id);
    if (params.channel) hp = hp.set('channel', params.channel);
    if (params.page) hp = hp.set('page', String(params.page));
    if (params.page_size) hp = hp.set('page_size', String(params.page_size));
    return this.http
      .get<RoomPerformanceDashboardDto>(`${this.apiConfig.baseUrl}/management/rates/analytics/room-performance`, { params: hp, withCredentials: true })
      .pipe(map(dto => mapRoomPerformanceDashboard(dto)));
  }

  /** Simple R2.2 dashboard: días con tarifa vs huecos (Mongo). */
  getRateCalendarDashboard(params: {
    prop_id?: number;
    plan_id?: string;
    date_from?: string;
    date_to?: string;
    days?: number;
    page?: number;
    page_size?: number;
  }) {
    let hp = new HttpParams();
    if (params.prop_id) hp = hp.set('prop_id', String(params.prop_id));
    if (params.plan_id) hp = hp.set('plan_id', params.plan_id);
    if (params.date_from) hp = hp.set('date_from', params.date_from);
    if (params.date_to) hp = hp.set('date_to', params.date_to);
    if (params.days) hp = hp.set('days', String(params.days));
    if (params.page) hp = hp.set('page', String(params.page));
    if (params.page_size) hp = hp.set('page_size', String(params.page_size));
    return this.http
      .get<RateCalendarDashboardDto>(`${this.apiConfig.baseUrl}/management/rates/analytics/rate-calendar`, { params: hp, withCredentials: true })
      .pipe(map(dto => mapRateCalendarDashboard(dto)));
  }

  /** Fetch amenity catalog labels for the given property (flatten grouped response).
   *
   * The API returns catalog as Array<{category, items: [{label, active, unit_price}]}> (grouped),
   * so we flatten it to Array<{category, label, unit_price, active}> for the UI checkbox grid.
   */
  getAmenityCatalog(propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http
      .get<{ catalog: { category: string; items: { label: string; unit_price: number; active: boolean }[] }[] }>(
        `${this.apiConfig.baseUrl}/management/amenities/options`,
        { params, withCredentials: true }
      )
      .pipe(map((res) => {
        const groups = res.catalog || [];
        const flat: { category: string; label: string; unit_price: number; active: boolean }[] = [];
        for (const group of groups) {
          for (const item of group.items || []) {
            flat.push({ category: group.category, label: item.label, unit_price: item.unit_price, active: item.active });
          }
        }
        return flat;
      }));
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
    applicableRoomTypes: string[];
    isActive: boolean;
    eligibleRoles?: string[];
    includedAmenities?: string[];
  }) {
    const params = new HttpParams().set('prop_id', String(payload.propId));
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rates/plans`,
      {
        prop_id: payload.propId,
        name: payload.name,
        description: payload.description,
        base_rate: payload.baseRate,
        currency: payload.currency,
        applicable_room_types: payload.applicableRoomTypes,
        is_active: payload.isActive,
        eligible_roles: payload.eligibleRoles ?? [],
        included_amenities: payload.includedAmenities ?? []
      },
      { params, withCredentials: true }
    );
  }

  updateRatePlan(propId: number, planId: string, payload: {
    name: string;
    description: string;
    baseRate: number;
    currency: string;
    applicableRoomTypes: string[];
    isActive: boolean;
    eligibleRoles?: string[];
    includedAmenities?: string[];
  }) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.put(
      `${this.apiConfig.baseUrl}/management/rates/plans/${planId}`,
      {
        name: payload.name,
        description: payload.description,
        base_rate: payload.baseRate,
        currency: payload.currency,
        applicable_room_types: payload.applicableRoomTypes,
        is_active: payload.isActive,
        eligible_roles: payload.eligibleRoles ?? [],
        included_amenities: payload.includedAmenities ?? []
      },
      { params, withCredentials: true }
    );
  }

  deleteRatePlan(propId: number, planId: string) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.delete(
      `${this.apiConfig.baseUrl}/management/rates/plans/${planId}`,
      { params, withCredentials: true }
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
    const params = new HttpParams().set('prop_id', String(payload.propId));
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
      { params, withCredentials: true }
    );
  }

  updateSeasonalRule(propId: number, ruleId: string, payload: {
    ratePlanId: string;
    name: string;
    startDate: string;
    endDate: string;
    priceOverride: number;
  }) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.put(
      `${this.apiConfig.baseUrl}/management/rates/seasonal-rules/${ruleId}`,
      {
        rate_plan_id: payload.ratePlanId,
        name: payload.name,
        start_date: payload.startDate,
        end_date: payload.endDate,
        price_override: payload.priceOverride
      },
      { params, withCredentials: true }
    );
  }

  deleteSeasonalRule(propId: number, ruleId: string) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.delete(
      `${this.apiConfig.baseUrl}/management/rates/seasonal-rules/${ruleId}`,
      { params, withCredentials: true }
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
    /** true = solo cuenta los días afectados (modal de confirmación), sin escribir. */
    dryRun?: boolean;
  }) {
    const params = new HttpParams().set('prop_id', String(payload.propId));
    return this.http.post<{ affected_days: number; start_date: string; end_date: string; rate_plan_id: string }>(
      `${this.apiConfig.baseUrl}/management/rates/calendar/batch`,
      {
        prop_id: payload.propId,
        rate_plan_id: payload.ratePlanId,
        start_date: payload.startDate,
        end_date: payload.endDate,
        rate_amount: payload.rateAmount,
        min_stay_nights: payload.minStayNights,
        is_closed: payload.isClosed,
        only_weekends: payload.onlyWeekends || false,
        dry_run: payload.dryRun ?? false
      },
      { params, withCredentials: true }
    );
  }

  generateCalendar(payload: {
    propId: number;
    ratePlanId?: string;
    startDate?: string;
    endDate?: string;
    /** true = solo cuenta las entradas que se crearían (modal de confirmación), sin escribir. */
    dryRun?: boolean;
  }) {
    const params = new HttpParams().set('prop_id', String(payload.propId));
    return this.http.post<{ plans_processed: number; entries_generated: number; start_date: string; end_date: string }>(
      `${this.apiConfig.baseUrl}/management/rates/calendar/generate`,
      {
        prop_id: payload.propId,
        rate_plan_id: payload.ratePlanId || '',
        start_date: payload.startDate || '',
        end_date: payload.endDate || '',
        dry_run: payload.dryRun ?? false,
      },
      { params, withCredentials: true }
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
    const params = new HttpParams().set('prop_id', String(payload.propId));
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
      { params, withCredentials: true }
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
    /**
     * La respuesta incluye coupons_retired: cuántos cupones se retiraron
     * (borrado lógico) al reducir coupon_count en este edit. La UI lo muestra
     * en el toast. KEEP IN SYNC con update_promotion_campaign (server).
     */
    return this.http.put<{ coupons_retired?: number }>(
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
    return this.http.get<PromotionsListResponse>(
      `${this.apiConfig.baseUrl}/management/promotions`,
      { params, withCredentials: true }
    );
  }
}

/** Wire shape de GET /api/management/promotions (list_property_campaigns). */
export interface PromotionCampaignDto {
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
  /** Cupones retirados (borrado lógico) — trazabilidad, no operativos. */
  coupon_deleted?: number;
  discount_percent_label?: string;
  hotel_label?: string;
}

export interface PromotionsListResponse {
  campaigns: PromotionCampaignDto[];
  total: number;
}
