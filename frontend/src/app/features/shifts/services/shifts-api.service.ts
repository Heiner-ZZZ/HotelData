import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

export interface ShiftInfo {
  id: string;
  prop_id: number;
  shift_type: string;
  employee: string;
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
  closed_by: string | null;
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

  /** Open a new shift */
  openShift(propId: number, shiftType: string, employee: string, cashInitial = 0) {
    return this.http.post<{ shift: ShiftInfo; message: string }>(
      '/api/reception/shifts/open',
      { prop_id: propId, shift_type: shiftType, employee, cash_initial: cashInitial },
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
