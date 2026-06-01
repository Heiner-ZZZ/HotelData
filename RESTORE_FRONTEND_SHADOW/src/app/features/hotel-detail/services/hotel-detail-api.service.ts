import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapHotelDetailResponse } from '../mappers/hotel-detail.mapper';
import type { HotelDetailDto } from '../models/hotel-detail.dto';

@Injectable({
  providedIn: 'root'
})
export class HotelDetailApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getHotelDetail(propId: number) {
    return this.http
      .get<HotelDetailDto>(`${this.apiConfig.baseUrl}/hotels/${propId}`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapHotelDetailResponse(dto)));
  }
}
