import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapHotelDetailResponse } from '../mappers/hotel-detail.mapper';
import type { HotelDetailDto, SimilarHotelDto, SimilarHotelsResponseDto } from '../models/hotel-detail.dto';
import type { SimilarHotel } from '../models/hotel-detail.model';
import { placeholderOrFallback } from '../../../shared/utils/placeholder-image.util';

export function mapSimilarHotel(dto: SimilarHotelDto): SimilarHotel {
  return {
    id: dto.prop_id,
    name: dto.hotel_label,
    stars: dto.prop_starrating ?? 0,
    reviewLabel: dto.review_label,
    location: dto.country_display_name,
    similarityScore: dto.similarity_score,
    reason: dto.reason,
    // Empty-string safe fallback: `dto.image_url` may be `""` if the
    // backend persists a half-configured row, and `<img src="">` never
    // fires `onError` (browser resolves to current page URL). Rejecting
    // the empty case keeps the `<img>` on the loremflickr URL, whose
    // eventual 404 will fire onError and surface the icon placeholder.
    imageUrl: placeholderOrFallback(dto.image_url, `${dto.prop_id}1`),
  };
}

@Injectable({
  providedIn: 'root'
})
export class HotelDetailApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getHotelDetail(hotelId: number) {
    return this.http
      .get<HotelDetailDto>(`${this.apiConfig.baseUrl}/hotels/${hotelId}`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapHotelDetailResponse(dto)));
  }

  getSimilarHotels(hotelId: number) {
    return this.http
      .get<SimilarHotelsResponseDto>(`${this.apiConfig.baseUrl}/hotels/${hotelId}/similar`, {
        withCredentials: true
      })
      .pipe(map((dto) => dto.items.map(mapSimilarHotel)));
  }
}
