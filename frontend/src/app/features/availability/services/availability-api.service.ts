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

@Injectable({
  providedIn: 'root'
})
export class AvailabilityApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getAvailability(propId: number, days = 90) {
    const params = new HttpParams()
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
    const params = new HttpParams()
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
    const params = new HttpParams().set('prop_id', String(payload.prop_id ?? ''));
    return this.http.patch(`${this.apiConfig.baseUrl}/management/availability`, payload, {
      params,
      withCredentials: true
    });
  }

  createBlackout(payload: AvailabilitySaveBlackoutDto) {
    const params = new HttpParams().set('prop_id', String(payload.prop_id ?? ''));
    return this.http.post(`${this.apiConfig.baseUrl}/management/availability/blackouts`, payload, {
      params,
      withCredentials: true
    });
  }  /** Fetch all hotel rooms for a property (for calendar room-number display). */
  getAllHotelRooms(propId: number) {
    return this.http.get<{ hotel_rooms: {
      hotel_room_id: string;
      room_number?: string;
      room_label: string;
      room_type_id: string;
      room_type_name?: string;
      floor?: string;
      is_active: boolean;
    }[] }>(
      `${this.apiConfig.baseUrl}/management/rooms`,
      {
        params: { prop_id: String(propId) },
        withCredentials: true
      }
    );
  }

  deleteBlackout(propId: number, blackoutId: string) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.delete(
      `${this.apiConfig.baseUrl}/management/availability/blackouts/${blackoutId}`,
      { params, withCredentials: true }
    );
  }

  deleteInventory(propId: number, roomTypeId: string, date: string) {
    return this.http.delete(`${this.apiConfig.baseUrl}/management/availability/inventory`, {
      params: { prop_id: String(propId), room_type_id: roomTypeId, date },
      withCredentials: true
    });
  }

  /** Fetch individual hotel rooms for a room type (multi-select support) */
  getHotelRooms(propId: number, roomTypeId: string) {
    return this.http.get<{ items: { hotel_room_id: string; room_number: string; room_label: string; floor: string; is_active: boolean }[]; total: number }>(
      `${this.apiConfig.baseUrl}/management/availability/hotel-rooms`,
      { params: { prop_id: String(propId), room_type_id: roomTypeId }, withCredentials: true }
    );
  }

  /** Update a future blackout block */
  updateBlackout(propId: number, blackoutId: string, payload: {
    start_date?: string;
    end_date?: string;
    reason?: string;
    room_numbers?: string[];
    blocked_rooms?: number;
  }) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.put(`${this.apiConfig.baseUrl}/management/availability/blackouts/${blackoutId}`, payload, {
      params,
      withCredentials: true
    });
  }
}
