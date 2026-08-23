import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { catchAuthError } from '../../../shared/utils/catch-auth-error';
import { mapAmenities, mapAmenitiesOptions } from '../mappers/amenities.mapper';
import type { AmenitiesDto, AmenitiesOptionsDto, AmenitiesSaveDto, SpecialRequestsSaveDto } from '../models/amenities.dto';

@Injectable({ providedIn: 'root' })
export class AmenitiesApiService {
  private readonly http = inject(HttpClient);

  getOptions(propId?: number) {
    let params = new HttpParams();
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http
      .get<AmenitiesOptionsDto>('/management/amenities/options', { params })
      .pipe(catchAuthError(), map((dto) => mapAmenitiesOptions(dto)));
  }

  /**
   * Save hotel amenities (Migración E): el backend exige ``prop_id`` en el
   * QUERY (gate por-hotel + consistencia query↔body) — el body solo no
   * alcanza (400).
   */
  saveAmenities(payload: AmenitiesSaveDto) {
    const params = new HttpParams().set('prop_id', String(payload.prop_id));
    return this.http.put<AmenitiesDto>('/management/amenities', payload, { params })
      .pipe(catchAuthError(), map((dto) => mapAmenities(dto)));
  }

  /** Save special requests — mismo gate por-hotel que saveAmenities. */
  saveSpecialRequests(payload: SpecialRequestsSaveDto) {
    const params = new HttpParams().set('prop_id', String(payload.prop_id));
    return this.http.put<{ special_requests: AmenitiesDto['special_requests']; high_floor_from: number }>(
      '/management/amenities/special-requests',
      payload,
      { params },
    ).pipe(catchAuthError());
  }
}
