import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { buildAvailabilityUpdateRequest, mapAvailabilitySnapshot } from '../mappers/availability.mapper';
import type { AvailabilitySnapshotDto } from '../models/availability.dto';
import type { AvailabilityRow } from '../models/availability.model';

@Injectable({
  providedIn: 'root',
})
export class AvailabilityApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getSnapshot(filters: {
    propId: number;
    roomTypeId?: string | null;
    ratePlanId?: string | null;
    startDate: string;
    endDate: string;
  }) {
    let params = new HttpParams()
      .set('prop_id', filters.propId)
      .set('start_date', filters.startDate)
      .set('end_date', filters.endDate);
    if (filters.roomTypeId) {
      params = params.set('room_type_id', filters.roomTypeId);
    }
    if (filters.ratePlanId) {
      params = params.set('rate_plan_id', filters.ratePlanId);
    }

    return this.http
      .get<AvailabilitySnapshotDto>(`${this.apiConfig.baseUrl}/management/availability`, {
        params,
        withCredentials: true,
      })
      .pipe(map((dto) => mapAvailabilitySnapshot(dto)));
  }

  getOptions(propId?: number) {
    let params = new HttpParams();
    if (propId) {
      params = params.set('prop_id', propId);
    }
    return this.http.get(`${this.apiConfig.baseUrl}/management/availability/options`, {
      params,
      withCredentials: true,
    });
  }

  saveUpdates(payload: {
    propId: number;
    roomTypeId: string;
    ratePlanId: string | null;
    rows: AvailabilityRow[];
  }) {
    return this.http.patch(
      `${this.apiConfig.baseUrl}/management/availability`,
      buildAvailabilityUpdateRequest(payload.propId, payload.roomTypeId, payload.ratePlanId, payload.rows),
      { withCredentials: true },
    );
  }
}
