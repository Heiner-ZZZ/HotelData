import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { catchAuthError } from '../../../shared/utils/catch-auth-error';
import { mapRoomCreatePayload, mapRoomsOptions, mapRoomsResponse } from '../mappers/rooms.mapper';
import type { FeatureCategory } from '../models/rooms.model';
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
    roomNumber?: string;
    floor?: string;
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
    roomNumber?: string;
    floor?: string;
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
        room_number: payload.roomNumber || '',
        floor: payload.floor || '',
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

  /* ── Room Features API ── */

  /** Get the master feature catalog, grouped by category (maps unit_price → unitPrice). */
  getFeatureCatalog() {
    return this.http
      .get<{ features: any[] }>(
        `${this.apiConfig.baseUrl}/management/room-features`,
        { withCredentials: true }
      )
      .pipe(map((res) => this._mapFeatureCatalog(res.features)));
  }

  private _mapFeatureCatalog(raw: any[]): FeatureCategory[] {
    return raw.map((cat: any) => ({
      category: cat.category,
      items: (cat.items || []).map((item: any) => ({
        label: item.label,
        category: item.category,
        icon: item.icon,
        custom: item.custom,
        unitPrice: typeof item.unit_price === 'number' ? item.unit_price : 0,
      })),
    }));
  }

  /** Get features for a specific room type. */
  getRoomTypeFeatures(propId: number, roomTypeId: string) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http
      .get<{ room_type_id: string; features: string[] }>(
        `${this.apiConfig.baseUrl}/management/room-features/${roomTypeId}`,
        { params, withCredentials: true }
      )
      .pipe(map((res) => res.features));
  }

  /** Update features (with optional unit_price) for a room type. */
  updateRoomTypeFeatures(propId: number, roomTypeId: string, features: Array<{ label: string; unitPrice?: number }>) {
    const params = new HttpParams().set('prop_id', String(propId));
    const payload = features.map((f) => ({
      label: f.label,
      unit_price: f.unitPrice ?? 0,
    }));
    return this.http.put(
      `${this.apiConfig.baseUrl}/management/room-features/${roomTypeId}`,
      { features: payload },
      { params, withCredentials: true }
    );
  }
}
