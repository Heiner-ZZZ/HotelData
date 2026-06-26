import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';

import { API_CONFIG } from '../../core/api/api.config';

export interface TopHotelRoomsItem {
  prop_id: number;
  label: string;
  room_types: number;
  physical_rooms: number;
}

export interface RateTrendSeries {
  plan_id: string;
  plan_name: string;
  data: { date: string; avg_rate: number }[];
}

export interface RateTrendResponse {
  dates: string[];
  series: RateTrendSeries[];
}

export interface CheckInOutHotelItem {
  prop_id: number;
  label: string;
  count: number;
}

export interface OperationalStatsResponse {
  total_hotels: number;
  total_policies: number;
  hotels_with_policies: number;
  check_ins_today: number;
  check_outs_today: number;
  check_ins_by_hotel: CheckInOutHotelItem[];
  check_outs_by_hotel: CheckInOutHotelItem[];
}

@Injectable({ providedIn: 'root' })
export class KpiApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly base = `${this.apiConfig.baseUrl}/kpi`;

  /** Top N hotels by room types + physical rooms */
  getTopHotelsByRooms(limit = 5): Observable<{ items: TopHotelRoomsItem[] }> {
    return this.http.get<{ items: TopHotelRoomsItem[] }>(
      `${this.base}/top-hotels/rooms?limit=${limit}`,
      { withCredentials: true }
    );
  }

  /** Rate trend over last 7 days for top N rate plans */
  getRateTrend(limitPlans = 5): Observable<RateTrendResponse> {
    return this.http.get<RateTrendResponse>(
      `${this.base}/rate-trend?limit_plans=${limitPlans}`,
      { withCredentials: true }
    );
  }

  /** Global operational stats for policies, check-ins, check-outs */
  getOperationalStats(): Observable<OperationalStatsResponse> {
    return this.http.get<OperationalStatsResponse>(
      `${this.base}/operational-stats`,
      { withCredentials: true }
    );
  }
}
