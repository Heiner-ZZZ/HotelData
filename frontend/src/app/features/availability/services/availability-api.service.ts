import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { catchAuthError } from '../../../shared/utils/catch-auth-error';
import { mapAvailability, mapAvailabilityPropertyOptions } from '../mappers/availability.mapper';
import type {
  AvailabilityDto,
  AvailabilitySaveBlackoutDto,
  AvailabilitySaveInventoryDto,
  ManagementPropertiesDto
} from '../models/availability.dto';
import type { PropertyOptionsPage } from '../models/availability.model';

@Injectable({
  providedIn: 'root'
})
export class AvailabilityApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getAvailability(propId: number, days = 90) {
    let params = new HttpParams()
      .set('prop_id', String(propId))
      .set('days', String(days));
    return this.http
      .get<AvailabilityDto>(`${this.apiConfig.baseUrl}/management/availability`, {
        params,
        withCredentials: true
      })
      .pipe(catchAuthError(), map((dto) => mapAvailability(dto)));
  }

  getPropertyOptions(q = '', page = 1, pageSize = 10) {
    let params = new HttpParams()
      .set('q', q)
      .set('page', String(page))
      .set('page_size', String(pageSize));
    return this.http
      .get<ManagementPropertiesDto>(`${this.apiConfig.baseUrl}/management/availability/options`, {
        params,
        withCredentials: true
      })
      .pipe(catchAuthError(), map((dto) => mapAvailabilityPropertyOptions(dto)));
  }

  getPropertyOptionsWithRooms(propId: number) {
    const params = new HttpParams()
      .set('prop_id', String(propId))
      .set('page_size', '10');
    return this.http
      .get<ManagementPropertiesDto>(`${this.apiConfig.baseUrl}/management/availability/options`, {
        params,
        withCredentials: true
      })
      .pipe(catchAuthError(), map((dto) => ({
        page: mapAvailabilityPropertyOptions(dto),
        roomTypes: dto.room_types ?? []
      })));
  }

  saveInventory(payload: AvailabilitySaveInventoryDto) {
    return this.http.patch(`${this.apiConfig.baseUrl}/management/availability`, payload, {
      withCredentials: true
    });
  }

  createBlackout(payload: AvailabilitySaveBlackoutDto) {
    return this.http.post(`${this.apiConfig.baseUrl}/management/availability/blackouts`, payload, {
      withCredentials: true
    });
  }

  deleteBlackout(blackoutId: string) {
    return this.http.delete(`${this.apiConfig.baseUrl}/management/availability/blackouts/${blackoutId}`, {
      withCredentials: true
    });
  }

  deleteInventory(propId: number, roomTypeId: string, date: string) {
    return this.http.delete(`${this.apiConfig.baseUrl}/management/availability/inventory`, {
      params: { prop_id: String(propId), room_type_id: roomTypeId, date },
      withCredentials: true
    });
  }
}
