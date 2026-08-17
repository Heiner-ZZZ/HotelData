import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { SHIFTS_MANAGE, type PermissionCode } from '../../../core/auth/permission.constants';

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
  /** Pagos confirmados estampados con este shift_id (depósitos/billing) que
   *  el drawer unificado agrega a las transacciones del array. */
  stamped_payments_count?: number;
  deposit_total?: number;
  deposits?: DepositRecord[];
  cash_difference?: number;
  cash_expected?: number;
  payment_ids?: string[];
  /** Resolved payments with their cashier attribution (manager cash-control). */
  payments?: ShiftPayment[];
  /** Per-employee totals of what each cashier collected in the shift
   *  (stamped payments grouped by responsible, for detecting discrepancies
   *  between stamped and deposited cash). */
  employee_summary?: EmployeeSummary[];
  folio_ids?: string[];
  booking_ids?: string[];
  /** Max-open-hours control: true when the shift is past its hotel limit. */
  is_expired?: boolean;
  /** Effective per-hotel max-open-hours limit (hours). */
  max_open_hours?: number;
  /** ISO timestamp when the shift reaches its max-open-hours limit. */
  expires_at?: string | null;
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

/** A payment collected during the shift, with its responsible cashier. */
export interface EmployeeSummary {
  employee: string;
  count: number;
  total: number;
  cash: number;
  card: number;
  transfer: number;
  other: number;
}

export interface ShiftPayment {
  payment_id: string;
  amount: number;
  method: string;
  reference: string | null;
  paid_at: string;
  /** Cashier attribution stamped on the payment (null when not shift-gated). */
  shift_employee: string | null;
  shift_opened_by: string | null;
  shift_type: string | null;
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

/** The three cashier shift buckets (hours are configurable per hotel). */
export const SHIFT_TYPES = ['morning', 'afternoon', 'evening'] as const;

export interface ShiftWindow {
  start: string;
  end: string;
}

/** Per-hotel shift-window config (windows + computed labels + audit). */
export interface ShiftConfig {
  prop_id: number;
  windows: Record<string, ShiftWindow>;
  labels: Record<string, string>;
  /** Max hours a shift may stay open before front-desk cash ops are blocked. */
  max_open_hours: number;
  /** Hours after which an internal heads-up notification is sent to the manager. */
  notify_manager_hours: number;
  is_custom: boolean;
  updated_at: string | null;
  updated_by: string | null;
}

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

/** One open shift across the chain (gerencia view: forgotten-shift detection). */
export interface OpenShiftOverview {
  id: string;
  prop_id: number;
  hotel_name: string;
  shift_type: string;
  /** Human label including the effective window, e.g. "Matutino (07:00-15:00)". */
  shift_label: string;
  employee: string;
  opened_by?: string | null;
  start_time: string;
  cash_initial: number;
  total_collected: number;
  /** Expected drawer breakdown by method (fondo + cobrado unificado), for
   *  the arqueo summary shown before a forced close. */
  payment_breakdown?: PaymentBreakdown;
  transaction_count: number;
  /** Hours since the shift was opened (age). */
  hours_open: number;
  /** Per-hotel max-open-hours limit. */
  max_open_hours: number;
  is_expired: boolean;
  expires_at: string | null;
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
  bypass_requires: PermissionCode;
  /** Whether the current authenticated user is ALLOWED to bypass. */
  opener_can_override: boolean;
}

/** Returned in the error.detail (HTTP 403) when bypass_schedule_check was
 *  sent without ``shifts.manage``. */
export interface ScheduleBypassForbiddenDetail {
  error: 'schedule_bypass_forbidden';
  message: string;
  bypass_requires: typeof SHIFTS_MANAGE;
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
   * @param shiftId         Shift to close.
   * @param cashCounted     Physical cash counted in the drawer.
   * @param cashLeft        Cash left in drawer for next shift (optional).
   * @param deposits        Deposit/drop records (optional).
   * @param closingNotes    Free-text observations (optional).
   * @param closedBy        User closing the shift (optional).
   * @param emergency       Manager-only emergency close of an expired shift
   *                        (simplified arqueo). Requires ``shifts.manage``.
   * @param emergencyReason Why the shift needed an emergency close
   *                        (defaults to ``vencimiento`` on the server).
   */
  closeShift(
    shiftId: string,
    cashCounted: number,
    cashLeft?: number,
    deposits?: DepositRecord[],
    closingNotes?: string,
    closedBy?: string,
    emergency?: boolean,
    emergencyReason?: string,
  ) {
    interface ShiftClosePayload {
      cash_counted: number;
      cash_left?: number;
      deposits?: DepositRecord[];
      closing_notes?: string;
      closed_by?: string;
      emergency?: boolean;
      emergency_reason?: string;
    }

    const body: ShiftClosePayload = { cash_counted: cashCounted };
    if (cashLeft !== undefined) body.cash_left = cashLeft;
    if (deposits?.length) body.deposits = deposits;
    if (closingNotes !== undefined) body.closing_notes = closingNotes;
    if (closedBy) body.closed_by = closedBy;
    if (emergency) {
      body.emergency = true;
      body.emergency_reason = emergencyReason || 'vencimiento';
    }

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
   * Requires `shifts.manage` permission.
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

  /** Effective shift-window config for a property (defaults when no custom doc). */
  getShiftConfig(propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.get<{ config: ShiftConfig }>(
      '/api/reception/shifts/config',
      { params, withCredentials: true },
    );
  }

  /**
   * Management view: every open cash shift across all hotels, with age.
   *
   * Requires `shifts.manage`.
   */
  getOpenShiftsOverview() {
    return this.http.get<{ items: OpenShiftOverview[]; total: number }>(
      '/api/reception/shifts/open-overview',
      { withCredentials: true },
    );
  }

  /**
   * Persist custom cash-shift windows (HH:MM start/end) for a property.
   *
   * Requires `shifts.manage`; the server rejects overlapping / malformed
   * windows with HTTP 400 and a Spanish detail message.
   */
  updateShiftConfig(
    propId: number,
    windows: Record<string, ShiftWindow>,
    maxOpenHours?: number,
    notifyManagerHours?: number,
  ) {
    const body: Record<string, unknown> = { prop_id: propId, windows };
    if (maxOpenHours !== null && maxOpenHours !== undefined) {
      body['max_open_hours'] = maxOpenHours;
    }
    if (notifyManagerHours !== null && notifyManagerHours !== undefined) {
      body['notify_manager_hours'] = notifyManagerHours;
    }
    return this.http.put<{ config: ShiftConfig; message: string }>(
      '/api/reception/shifts/config',
      body,
      { withCredentials: true },
    );
  }
}
