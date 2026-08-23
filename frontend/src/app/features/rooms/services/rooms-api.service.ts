import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { catchAuthError } from '../../../shared/utils/catch-auth-error';
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
      .pipe(catchAuthError(), map((dto) => mapRoomsResponse(dto)));
  }

  getOptions() {
    return this.http
      .get<RoomsOptionsDto>(`${this.apiConfig.baseUrl}/management/rooms/options`, {
        withCredentials: true
      })
      .pipe(catchAuthError(), map((dto) => mapRoomsOptions(dto)));
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
    imageUrl?: string;
    roomNumber?: string;
    floor?: string;
    view?: string;
    smoking?: boolean;
    accessible?: boolean;
  }) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rooms`,
      mapRoomCreatePayload(payload),
      { withCredentials: true }
    ).pipe(catchAuthError());
  }

  updateRoomType(propId: number, roomTypeId: string, payload: {
    name: string;
    description: string;
    maxAdults: number;
    maxChildren: number;
    baseCapacity: number;
    baseRate?: number;
    isActive: boolean;
    imageUrl?: string;
    roomNumber?: string;
    floor?: string;
    view?: string;
    smoking?: boolean;
    accessible?: boolean;
  }) {
    const params = new HttpParams().set('prop_id', String(propId));
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
        room_number: payload.roomNumber || '',
        floor: payload.floor || '',
        view: payload.view || '',
        smoking: payload.smoking ?? false,
        accessible: payload.accessible ?? false,
        image_url: payload.imageUrl || '',
      },
      { params, withCredentials: true }
    );
  }

  createHotelRoomForType(propId: number, roomTypeId: string, payload: {
    roomNumber: string;
    floor?: string;
    view?: string;
    smoking?: boolean;
    accessible?: boolean;
    isActive?: boolean;
  }) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/rooms/${roomTypeId}/rooms`,
      {
        room_number: payload.roomNumber,
        floor: payload.floor || '',
        view: payload.view || '',
        smoking: payload.smoking ?? false,
        accessible: payload.accessible ?? false,
        is_active: payload.isActive ?? true,
      },
      { params, withCredentials: true }
    );
  }

  deleteRoomType(propId: number, roomTypeId: string) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.delete(
      `${this.apiConfig.baseUrl}/management/rooms/${roomTypeId}`,
      { params, withCredentials: true }
    );
  }

  uploadRoomImage(propId: number, roomTypeId: string, file: File) {
    const params = new HttpParams().set('prop_id', String(propId));
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<{ image_url: string }>(
      `${this.apiConfig.baseUrl}/management/rooms/${roomTypeId}/image`,
      formData,
      { params, withCredentials: true }
    );
  }

  /* ── Room Features API ── */

  /** Get features for a specific room type. */
  getRoomTypeFeatures(propId: number, roomTypeId: string) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http
      .get<{ room_type_id: string; features: { label: string }[] }>(
        `${this.apiConfig.baseUrl}/management/room-features/${roomTypeId}`,
        { params, withCredentials: true }
      )
      .pipe(map((res) => res.features));
  }

  /** Update features for a room type. */
  updateRoomTypeFeatures(propId: number, roomTypeId: string, features: { label: string }[]) {
    const params = new HttpParams().set('prop_id', String(propId));
    const payload = features.map((f) => ({ label: f.label }));
    return this.http.put(
      `${this.apiConfig.baseUrl}/management/room-features/${roomTypeId}`,
      { features: payload },
      { params, withCredentials: true }
    );
  }
}
