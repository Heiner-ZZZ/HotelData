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
    isActive: boolean;
  }) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rooms`,
      mapRoomCreatePayload(payload),
      { withCredentials: true }
    );
  }
}
