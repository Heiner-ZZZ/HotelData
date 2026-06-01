import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, switchMap, throwError } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { buildCreateRoomTypeRequest, mapRoomsResponse } from '../mappers/rooms.mapper';
import type {
  RoomsOptionsResponseDto,
  RoomsSnapshotResponseDto
} from '../models/rooms.dto';

@Injectable({
  providedIn: 'root'
})
export class RoomsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getRooms(propId: number) {
    const requestedParams = propId > 0 ? new HttpParams().set('prop_id', propId) : undefined;
    return this.http
      .get<RoomsOptionsResponseDto>(`${this.apiConfig.baseUrl}/management/rooms/options`, {
        params: requestedParams,
        withCredentials: true
      })
      .pipe(
        switchMap((options) => {
          const selectedPropId = options.selected_prop_id;
          if (!selectedPropId) {
            return throwError(() => new Error('No hay propiedades disponibles para habitaciones.'));
          }

          return this.http
            .get<RoomsSnapshotResponseDto>(`${this.apiConfig.baseUrl}/management/rooms`, {
              params: new HttpParams().set('prop_id', selectedPropId),
              withCredentials: true
            })
            .pipe(map((snapshot) => mapRoomsResponse(options, snapshot)));
        })
      );
  }

  createRoomType(
    propId: number,
    value: {
      name: string;
      description: string;
      maxAdults: number;
      maxChildren: number;
      baseCapacity: number;
      isActive: boolean;
    }
  ) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rooms`,
      buildCreateRoomTypeRequest(propId, value),
      {
        withCredentials: true
      }
    );
  }
}
