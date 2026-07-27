import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

export interface ShiftInfo {
  id: string;
  prop_id: number;
  shift_type: string;
  /** Visual label of the recepcionista (free text typed by the user). */
  employee: string;
  /** ObjectId FK to `employees` collection resolved from `employee` name. May be null. */
  employee_id?: string | null;
  /** Audit-grade: server-controlled authenticated user that OPENED the shift. */
  opened_by?: string;
  /** ObjectId FK to `users` collection — the actual IAM principal who opened the shift. */
  opened_by_id?: string | null;
  start_time: string;
  end_time: string | null;
  cash_initial: number;
  cash_counted: number | null;
  cash_final: number | null;
  cash_left: number | null;
  cash_over_short: number | null;
  closing_notes: string | null;
  total_collected: number;
  status: string;
  /** Audit-grade: server-controlled authenticated user that CLOSED the shift. */
  closed_by: string | null;
  /** ObjectId FK to `users` collection — the actual IAM principal who closed the shift. */
  closed_by_id?: string | null;
  closed_at: string | null;
  transactions: ShiftTransaction[];
  payment_breakdown?: PaymentBreakdown;
  deposit_total?: number;
  deposits?: DepositRecord[];
  cash_difference?: number;
  cash_expected?: number;
  payment_ids?: string[];
  folio_ids?: string[];
  booking_ids?: string[];
}

export interface ShiftTransaction {
  transaction_id: string;
  type: string;
  booking_id: string;
  amount: number;
  payment_method: string;
  timestamp: string;
  description: string;
}

export interface PaymentBreakdown {
  cash: number;
  card: number;
  transfer: number;
  other: number;
  total: number;
}

export interface DepositRecord {
  amount: number;
  method: string;
  notes: string;
}

/** Methods that reduce the physical cash left in the drawer. */
export const CASH_DEPOSIT_METHODS = ['cash', 'efectivo', ''];

export interface ShiftCloseSummary {
  cash_initial: number;
  cash_final: number;
  cash_counted: number;
  cash_left: number;
  total_collected: number;
  cash_difference: number;
  cash_expected: number;
  cash_over_short: number;
  transaction_count: number;
  payment_breakdown: PaymentBreakdown;
  deposit_total: number;
  closing_notes: string;
  payment_count: number;
  folio_count: number;
  booking_count: number;
}

/** Returned in the error.detail when POST /shifts/open hits an active shift. */
export interface ActiveShiftConflict {
  error: 'active_shift_exists';
  message: string;
  active_shift: ShiftInfo;
  transactions_count: number;
  total_collected: number;
  last_closed_over_short: number | null;
  force_blocked_by_over_short: boolean;
}

/** Returned in the error.detail (HTTP 422) when the opener requested a
 *  shift_type that doesn't match the expected cash-window for NOW.
 *  The frontend uses ``opener_can_override`` to decide whether to show
 *  the gerente-only override checkbox; the bypass still requires
 *  ``shifts.manage`` server-side. */
export interface ScheduleMismatchDetail {
  error: 'schedule_mismatch';
  requested: string;
  expected: string;
  /** Human-friendly range like '08:00-16:00' or '16:00-00:00'. */
  expected_window: string;
  /** 'schedule' (HR lookup) or 'time_of_day' (clock fallback). */
  source: 'schedule' | 'time_of_day';
  /** ISO 8601 UTC timestamp of the moment the server resolved 'now'. */
  now_utc: string;
  /** Username that opened the shift (server-derived, not client-derived). */
  opener: string;
  message: string;
  /** Permission code the opener must hold to invoke bypass_schedule_check. */
  bypass_requires: 'shifts.manage';
  /** Whether the current authenticated user is ALLOWED to bypass. */
  opener_can_override: boolean;
}

/** Returned in the error.detail (HTTP 403) when bypass_schedule_check was
 *  sent without ``shifts.manage``. */
export interface ScheduleBypassForbiddenDetail {
  error: 'schedule_bypass_forbidden';
  message: string;
  bypass_requires: 'shifts.manage';
}

@Injectable({ providedIn: 'root' })
export class ShiftsApiService {
  private readonly http = inject(HttpClient);

  /** Get currently active shift for a property */
  getActiveShift(propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.get<{ shift: ShiftInfo | null; shift_type_labels: Record<string, string> }>(
      '/api/reception/shifts/active',
      { params, withCredentials: true },
    );
  }

  /**
   * Open a new shift.
   *
   * Set ``force: true`` to auto-close a currently-active shift without
   * reconciliation. The server still rejects force when the most recent
   * closed shift had a non-zero ``cash_over_short`` — the modal in the
   * UI surfaces this via ``force_blocked_by_over_short``.
   *
   * Set ``bypassScheduleCheck: true`` to override the schedule validation
   * (server requires ``shifts.manage`` permission; otherwise HTTP 403).
   */
  openShift(
    propId: number,
    shiftType: string,
    employee: string,
    cashInitial: number | null = null,
    options: { force?: boolean; bypassScheduleCheck?: boolean } = {},
  ) {
    const body: Record<string, unknown> = {
      prop_id: propId,
      shift_type: shiftType,
      employee,
    };
    if (cashInitial !== null && cashInitial !== undefined) {
      body['cash_initial'] = cashInitial;
    }
    if (options.force) {
      body['force'] = true;
    }
    if (options.bypassScheduleCheck) {
      body['bypass_schedule_check'] = true;
    }
    return this.http.post<{ shift: ShiftInfo; message: string }>(
      '/api/reception/shifts/open',
      body,
      { withCredentials: true },
    );
  }

  /** Close an active shift with full cash register data.
   *
   * @param shiftId      Shift to close.
   * @param cashCounted  Physical cash counted in the drawer.
   * @param cashLeft     Cash left in drawer for next shift (optional).
   * @param deposits     Deposit/drop records (optional).
   * @param closingNotes Free-text observations (optional).
   * @param closedBy     User closing the shift (optional).
   */
  closeShift(
    shiftId: string,
    cashCounted: number,
    cashLeft?: number,
    deposits?: DepositRecord[],
    closingNotes?: string,
    closedBy?: string,
  ) {
    interface ShiftClosePayload {
      cash_counted: number;
      cash_left?: number;
      deposits?: DepositRecord[];
      closing_notes?: string;
      closed_by?: string;
    }

    const body: ShiftClosePayload = { cash_counted: cashCounted };
    if (cashLeft !== undefined) body.cash_left = cashLeft;
    if (deposits?.length) body.deposits = deposits;
    if (closingNotes !== undefined) body.closing_notes = closingNotes;
    if (closedBy) body.closed_by = closedBy;

    return this.http.post<{ shift: ShiftInfo; message: string; summary: ShiftCloseSummary }>(
      `/api/reception/shifts/${shiftId}/close`,
      body,
      { withCredentials: true },
    );
  }

  /** Get shift detail by ID */
  getShift(shiftId: string) {
    return this.http.get<{ shift: ShiftInfo }>(
      `/api/reception/shifts/${shiftId}`,
      { withCredentials: true },
    );
  }

  /** List shifts */
  listShifts(propId?: number, status?: string, limit = 50) {
    let params = new HttpParams();
    if (propId) params = params.set('prop_id', String(propId));
    if (status) params = params.set('status', status);
    if (limit) params = params.set('limit', String(limit));
    return this.http.get<{ items: ShiftInfo[]; total: number }>(
      '/api/reception/shifts',
      { params, withCredentials: true },
    );
  }

  /** Manager cash-control view: closed shifts with over/short details.
   *
   * Requires `billing.manage` permission.
   */
  listShiftsForCashControl(
    propId?: number,
    startDate?: string,
    endDate?: string,
    limit = 50,
  ) {
    let params = new HttpParams();
    if (propId) params = params.set('prop_id', String(propId));
    if (startDate) params = params.set('start_date', startDate);
    if (endDate) params = params.set('end_date', endDate);
    if (limit) params = params.set('limit', String(limit));
    return this.http.get<{ items: ShiftInfo[]; total: number }>(
      '/api/reception/shifts/manager-control',
      { params, withCredentials: true },
    );
  }
}
