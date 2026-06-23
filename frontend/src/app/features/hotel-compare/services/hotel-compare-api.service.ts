import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapHotelCompareResponse } from '../mappers/hotel-compare.mapper';
import type { HotelCompareDto } from '../models/hotel-compare.dto';

@Injectable({
  providedIn: 'root'
})
export class HotelCompareApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  compare(
    propIds: number[],
    checkIn?: string,
    checkOut?: string,
    adults?: number,
    children?: number
  ) {
    let params = new HttpParams();
    for (const pid of propIds.slice(0, 3)) {
      params = params.append('prop_id', String(pid));
    }
    if (checkIn) params = params.set('check_in', checkIn);
    if (checkOut) params = params.set('check_out', checkOut);
    if (adults) params = params.set('adults', String(adults));
    if (children) params = params.set('children', String(children));

    return this.http
      .get<HotelCompareDto>(`${this.apiConfig.baseUrl}/hotels/compare`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapHotelCompareResponse(dto)));
  }
}
