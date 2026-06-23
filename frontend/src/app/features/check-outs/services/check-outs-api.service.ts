import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapCheckOuts } from '../mappers/check-outs.mapper';
import type { CheckOutsDto } from '../models/check-outs.dto';

export interface DateHistoryEntry {
  date: string;
  count: number;
  prop_id?: number;
  hotel_label?: string;
}

@Injectable({ providedIn: 'root' })
export class CheckOutsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getCheckOuts(operationDate: string, propId?: number) {
    let params = new HttpParams().set('date', operationDate);
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http
      .get<CheckOutsDto>(`${this.apiConfig.baseUrl}/management/check-outs`, { params, withCredentials: true })
      .pipe(map((dto) => mapCheckOuts(dto)));
  }

  getCheckOutDates(propId?: number) {
    let params = new HttpParams();
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http.get<DateHistoryEntry[]>(`${this.apiConfig.baseUrl}/management/check-outs/dates`, {
      params,
      withCredentials: true
    });
  }

  completeCheckOut(bookingId: string) {
    return this.http.post(`${this.apiConfig.baseUrl}/management/check-outs/${bookingId}/complete`, {}, { withCredentials: true });
  }
}
