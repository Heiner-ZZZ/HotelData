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
    let params = new HttpParams()
      .set('page', String(normalized.page))
      .set('page_size', '10');

    const paramMap: Record<string, string | number | undefined> = {
      destination: normalized.destination || undefined,
      check_in: normalized.checkIn || undefined,
      check_out: normalized.checkOut || undefined,
      adults: Number(normalized.adults) || undefined,
      children: Number(normalized.children) || undefined,
      rooms: Number(normalized.rooms) || undefined,
      price_min: normalized.minPrice ? Number(normalized.minPrice) : undefined,
      price_max: normalized.maxPrice ? Number(normalized.maxPrice) : undefined,
      star_rating: normalized.minStars ? Number(normalized.minStars) : undefined,
      amenities: (Array.isArray(normalized.amenities) ? normalized.amenities.join(',') : normalized.amenities) || undefined,
      amenities_mode: normalized.amenitiesMode || undefined,
      sort_by: normalized.sortBy || undefined,
    };

    for (const [key, value] of Object.entries(paramMap)) {
      if (value !== undefined && value !== '') {
        params = params.set(key, String(value));
      }
    }

    return this.http
      .get<HotelSearchDto>(`${this.apiConfig.baseUrl}/hotels/availability`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapHotelSearchResponse(dto, normalized)));
  }
}
