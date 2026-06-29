import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';

export interface ReceptionShift {
  id: string;
  prop_id: number;
  shift_type: 'morning' | 'afternoon' | 'evening';
  employee: string;
  start_time: string;
  end_time: string | null;
  cash_initial: number;
  cash_final: number | null;
  total_collected: number;
  status: 'open' | 'closed';
  closed_by: string | null;
  closed_at: string | null;
  transactions: ShiftTransaction[];
  created_at: string;
  cash_difference?: number;
  cash_expected?: number;
}

export interface ShiftTransaction {
  transaction_id: string;
  type: 'check_in' | 'check_out' | 'payment' | 'cancellation';
  booking_id: string;
  amount: number;
  payment_method: string;
  timestamp: string;
  description: string;
}

export interface ShiftOpenPayload {
  prop_id: number;
  shift_type: 'morning' | 'afternoon' | 'evening';
  employee: string;
  cash_initial?: number;
}

export interface ShiftClosePayload {
  cash_final: number;
  closed_by?: string;
}

export interface ShiftResponse {
  shift: ReceptionShift | null;
  shift_type_labels?: Record<string, string>;
  message?: string;
  summary?: ShiftCloseSummary;
}

export interface ShiftCloseSummary {
  cash_initial: number;
  cash_final: number;
  total_collected: number;
  cash_difference: number;
  cash_expected: number;
  transaction_count: number;
}

export interface ShiftListResponse {
  items: ReceptionShift[];
  total: number;
}

@Injectable({ providedIn: 'root' })
export class ReceptionApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  private get baseUrl() {
    return `${this.apiConfig.baseUrl}/reception`;
  }

  /** Get the currently active (open) shift for a property. */
  getActiveShift(propId: number): Observable<ShiftResponse> {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.get<ShiftResponse>(`${this.baseUrl}/shifts/active`, {
      params,
      withCredentials: true,
    });
  }

  /** Open a new reception shift. */
  openShift(payload: ShiftOpenPayload): Observable<ShiftResponse> {
    return this.http.post<ShiftResponse>(`${this.baseUrl}/shifts/open`, payload, {
      withCredentials: true,
    });
  }

  /** Close an active shift. */
  closeShift(shiftId: string, payload: ShiftClosePayload): Observable<ShiftResponse> {
    return this.http.post<ShiftResponse>(
      `${this.baseUrl}/shifts/${shiftId}/close`,
      payload,
      { withCredentials: true },
    );
  }

  /** Get detail of a specific shift by ID. */
  getShift(shiftId: string): Observable<ShiftResponse> {
    return this.http.get<ShiftResponse>(`${this.baseUrl}/shifts/${shiftId}`, {
      withCredentials: true,
    });
  }

  /** List shifts with optional filters. */
  listShifts(
    propId?: number,
    status?: string,
    limit = 50,
  ): Observable<ShiftListResponse> {
    let params = new HttpParams();
    if (propId) params = params.set('prop_id', String(propId));
    if (status) params = params.set('status', status);
    if (limit) params = params.set('limit', String(limit));
    return this.http.get<ShiftListResponse>(`${this.baseUrl}/shifts`, {
      params,
      withCredentials: true,
    });
  }
}
