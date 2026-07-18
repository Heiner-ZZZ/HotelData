import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapHotelOption, mapListItem, mapPayload, mapResult, mapRoomTypeOption } from '../mappers/manual-reservation.mapper';
import type { ManualReservationListItemDto, ManualReservationResultDto } from '../models/manual-reservation.dto';
import type { HotelOption, ManualReservationInput, ManualReservationListItem, RoomTypeOption } from '../models/manual-reservation.model';

interface AvailabilityOptionsResponse {
  properties: { prop_id: number; display_name: string }[];
  room_types?: {
    room_type_id: string;
    name: string;
    max_adults: number;
    max_children: number;
    base_capacity: number;
    is_active: boolean;
  }[];
}

@Injectable({
  providedIn: 'root'
})
export class ManualReservationApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  /** Get hotel options for the select dropdown. */
  getHotelOptions() {
    return this.http
      .get<AvailabilityOptionsResponse>(
        `${this.apiConfig.baseUrl}/management/availability/options`,
        { withCredentials: true }
      )
      .pipe(map((dto) => (dto.properties || []).map(mapHotelOption)));
  }

  /** Get room types for a specific hotel (fetched via availability/options with prop_id). */
  getRoomTypes(propId: number) {
    return this.http
      .get<AvailabilityOptionsResponse>(
        `${this.apiConfig.baseUrl}/management/availability/options`,
        {
          params: { prop_id: String(propId) },
          withCredentials: true
        }
      )
      .pipe(map((dto) => (dto.room_types || []).map(mapRoomTypeOption)));
  }

  /** List manual reservations */
  getManualReservations(page = 1) {
    const params = new HttpParams().set('page', String(page));
    return this.http
      .get<{ items: ManualReservationListItemDto[]; page: number; total: number; has_next: boolean; has_prev: boolean }>(
        `${this.apiConfig.baseUrl}/management/manual-reservations`,
        { params, withCredentials: true }
      )
      .pipe(map((dto) => ({
        items: dto.items.map(mapListItem),
        page: dto.page,
        total: dto.total,
        hasNext: dto.has_next,
        hasPrev: dto.has_prev,
      })));
  }

  /** Create a manual reservation. */
  createManualReservation(input: ManualReservationInput) {
    return this.http
      .post<ManualReservationResultDto>(
        `${this.apiConfig.baseUrl}/management/manual-reservations`,
        mapPayload(input),
        { withCredentials: true }
      )
      .pipe(map((dto) => mapResult(dto)));
  }
}
