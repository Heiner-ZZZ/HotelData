import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapRoomCreatePayload, mapRoomsOptions, mapRoomsResponse } from '../mappers/rooms.mapper';
import type { RoomsDto, RoomsOptionsDto } from '../models/rooms.dto';

@Injectable({
  providedIn: 'root'
})
export class RoomsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getRooms(propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http
      .get<RoomsDto>(`${this.apiConfig.baseUrl}/management/rooms`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapRoomsResponse(dto)));
  }

  getOptions() {
    return this.http
      .get<RoomsOptionsDto>(`${this.apiConfig.baseUrl}/management/rooms/options`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapRoomsOptions(dto)));
  }

  createRoomType(payload: {
    propId: number;
    name: string;
    description: string;
    maxAdults: number;
    maxChildren: number;
    baseCapacity: number;
    baseRate?: number;
    isActive: boolean;
  }) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rooms`,
      mapRoomCreatePayload(payload),
      { withCredentials: true }
    );
  }

  updateRoomType(roomTypeId: string, payload: {
    name: string;
    description: string;
    maxAdults: number;
    maxChildren: number;
    baseCapacity: number;
    baseRate?: number;
    isActive: boolean;
  }) {
    return this.http.put(
      `${this.apiConfig.baseUrl}/management/rooms/${roomTypeId}`,
      {
        name: payload.name,
        description: payload.description,
        max_adults: payload.maxAdults,
        max_children: payload.maxChildren,
        base_capacity: payload.baseCapacity,
        base_rate: payload.baseRate,
        is_active: payload.isActive,
      },
      { withCredentials: true }
    );
  }

  deleteRoomType(roomTypeId: string) {
    return this.http.delete(
      `${this.apiConfig.baseUrl}/management/rooms/${roomTypeId}`,
      { withCredentials: true }
    );
  }
}
