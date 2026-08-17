import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, catchError, finalize, of } from 'rxjs';

import { API_CONFIG } from '../../core/api/api.config';

export interface OpenCashShift {
  id: string;
  prop_id: number;
  hotel_label: string;
  shift_number?: number;
  shift_type: string;
  shift_label: string;
  employee: string;
  opened_by?: string | null;
  start_time?: string;
}

export interface OpenAttendanceShift {
  id: string;
  employee_id: string;
  employee_name: string;
  date: string;
  scheduled_start: string;
  scheduled_end: string;
  area: string;
  status: string;
}

export interface LogoutGuardResponse {
  has_open_shifts: boolean;
  open_cash_shifts: OpenCashShift[];
  open_attendance_shift: OpenAttendanceShift | null;
}

/**
 * Self-scoped pre-logout check: does the current user have an open cash
 * shift (reception_shifts) or an open attendance shift (employee_shifts)?
 *
 * The management top-nav calls {@link check} when "Cerrar sesión" is
 * clicked and, if the server reports open shifts, shows a confirmation
 * modal with deep links instead of logging out silently.
 *
 * Fail-open by design: any network/HTTP error resolves to "no open
 * shifts" so a server blip never blocks the logout.
 */
@Injectable({ providedIn: 'root' })
export class LogoutGuardService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  /** True while the guard request is in flight (spinner in the logout button). */
  readonly checking = signal(false);

  check(): Observable<LogoutGuardResponse> {
    this.checking.set(true);
    return this.http
      .get<LogoutGuardResponse>(`${this.apiConfig.baseUrl}/auth/logout-guard`, {
        withCredentials: true,
      })
      .pipe(
        finalize(() => this.checking.set(false)),
        catchError(() =>
          of<LogoutGuardResponse>({
            has_open_shifts: false,
            open_cash_shifts: [],
            open_attendance_shift: null,
          }),
        ),
      );
  }
}
