import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { createHotelSearchFilters, mapHotelSearchResponse } from '../mappers/hotel-search.mapper';
import type { HotelSearchDto } from '../models/hotel-search.dto';
import type { HotelSearchFilters } from '../models/hotel-search.model';

@Injectable({
  providedIn: 'root'
})
export class HotelSearchApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  search(filters: Partial<HotelSearchFilters>) {
    const normalized = createHotelSearchFilters(filters);
    let params = new HttpParams().set('page', String(normalized.page));

    const paramMap = {
      destination: normalized.destination,
      min_price: normalized.minPrice,
      max_price: normalized.maxPrice,
      min_stars: normalized.minStars,
      promotion: normalized.promotion,
      adults: normalized.adults,
      children: normalized.children,
      rooms: normalized.rooms
    };

    for (const [key, value] of Object.entries(paramMap)) {
      if (value) {
        params = params.set(key, value);
      }
    }

    return this.http
      .get<HotelSearchDto>(`${this.apiConfig.baseUrl}/hotels/search`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapHotelSearchResponse(dto)));
  }
}
