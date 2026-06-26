import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Service } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { catchAuthError } from '../../../shared/utils/catch-auth-error';
import { mapAmenities, mapAmenitiesOptions } from '../mappers/amenities.mapper';
import type { AmenitiesDto, AmenitiesOptionsDto, AmenitiesSaveDto } from '../models/amenities.dto';

@Service()
export class AmenitiesApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getOptions(propId?: number) {
    let params = new HttpParams();
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http
      .get<AmenitiesOptionsDto>(`${this.apiConfig.baseUrl}/management/amenities/options`, {
        params,
        withCredentials: true
      })
      .pipe(catchAuthError(), map((dto) => mapAmenitiesOptions(dto)));
  }

  getAmenities(propId: number, roomTypeId = '') {
    let params = new HttpParams().set('prop_id', String(propId));
    if (roomTypeId) {
      params = params.set('room_type_id', roomTypeId);
    }
    return this.http
      .get<AmenitiesDto>(`${this.apiConfig.baseUrl}/management/amenities`, {
        params,
        withCredentials: true
      })
      .pipe(catchAuthError(), map((dto) => mapAmenities(dto)));
  }

  saveAmenities(payload: AmenitiesSaveDto) {
    return this.http.put<AmenitiesDto>(`${this.apiConfig.baseUrl}/management/amenities`, payload, {
      withCredentials: true
    }).pipe(catchAuthError(), map((dto) => mapAmenities(dto)));
  }
}
