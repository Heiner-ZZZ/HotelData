import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { API_CONFIG } from '../../../core/api/api.config';
import type { GuestAmenityCatalogDto, GuestAmenityRequestDto, GuestAmenityRequestResponseDto } from '../models/guest-amenity.dto';

@Injectable({ providedIn: 'root' })
export class GuestAmenityService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getCatalog(bookingId: string) {
    const params = new HttpParams().set('booking_id', bookingId);
    return this.http.get<GuestAmenityCatalogDto>(
      `${this.apiConfig.baseUrl}/amenities/guest/catalog`,
      { params },
    );
  }

  getCatalogByProp(propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.get<{ catalog: GuestAmenityCatalogDto['catalog'] }>(
      `${this.apiConfig.baseUrl}/amenities/guest/catalog/by-prop`,
      { params },
    );
  }

  requestAmenities(payload: GuestAmenityRequestDto) {
    return this.http.post<GuestAmenityRequestResponseDto>(
      `${this.apiConfig.baseUrl}/amenities/guest/request`,
      payload,
    );
  }
}
