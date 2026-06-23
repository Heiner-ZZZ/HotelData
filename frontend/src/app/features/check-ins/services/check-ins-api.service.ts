import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapCheckIns } from '../mappers/check-ins.mapper';
import type { CheckInsDto } from '../models/check-ins.dto';

export interface DateHistoryEntry {
  date: string;
  count: number;
  prop_id?: number;
  hotel_label?: string;
}

@Injectable({ providedIn: 'root' })
export class CheckInsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getCheckIns(operationDate: string, propId?: number) {
    let params = new HttpParams().set('date', operationDate);
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http
      .get<CheckInsDto>(`${this.apiConfig.baseUrl}/management/check-ins`, { params, withCredentials: true })
      .pipe(map((dto) => mapCheckIns(dto)));
  }

  getCheckInDates(propId?: number) {
    let params = new HttpParams();
    if (propId) {
      params = params.set('prop_id', String(propId));
    }
    return this.http.get<DateHistoryEntry[]>(`${this.apiConfig.baseUrl}/management/check-ins/dates`, {
      params,
      withCredentials: true
    });
  }

  completeCheckIn(bookingId: string) {
    return this.http.post(`${this.apiConfig.baseUrl}/management/check-ins/${bookingId}/complete`, {}, { withCredentials: true });
  }
}
