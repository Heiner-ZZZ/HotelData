import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapHotelSearchResponse } from '../mappers/hotel-search.mapper';
import type { HotelSearchResponseDto } from '../models/hotel-search.dto';
import type { HotelSearchFilters } from '../models/hotel-search.model';

@Injectable({
  providedIn: 'root'
})
export class HotelSearchApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  searchHotels(filters: HotelSearchFilters, page: number) {
    let params = new HttpParams().set('page', page);

    const entries: Array<[string, string]> = [
      ['destination', filters.destination],
      ['min_price', filters.minPrice],
      ['max_price', filters.maxPrice],
      ['min_stars', filters.minStars],
      ['promotion', filters.promotion],
      ['adults', filters.adults],
      ['children', filters.children],
      ['rooms', filters.rooms]
    ];

    for (const [key, value] of entries) {
      if (value.trim()) {
        params = params.set(key, value.trim());
      }
    }

    return this.http
      .get<HotelSearchResponseDto>(`${this.apiConfig.baseUrl}/hotels/search`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapHotelSearchResponse(dto)));
  }
}
