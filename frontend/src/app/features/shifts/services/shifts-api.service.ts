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
  cash_final: number | null;
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

export interface ShiftCloseSummary {
  cash_initial: number;
  cash_final: number;
  total_collected: number;
  cash_difference: number;
  cash_expected: number;
  transaction_count: number;
  payment_breakdown: PaymentBreakdown;
  deposit_total: number;
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
  openShift(propId: number, shiftType: string, employee: string, cashInitial: number = 0) {
    return this.http.post<{ shift: ShiftInfo; message: string }>(
      '/api/reception/shifts/open',
      { prop_id: propId, shift_type: shiftType, employee, cash_initial: cashInitial },
      { withCredentials: true },
    );
  }

  /** Close an active shift */
  closeShift(shiftId: string, cashFinal: number, deposits?: DepositRecord[], closedBy?: string) {
    return this.http.post<{ shift: ShiftInfo; message: string; summary: ShiftCloseSummary }>(
      `/api/reception/shifts/${shiftId}/close`,
      { cash_final: cashFinal, deposits: deposits || [], closed_by: closedBy },
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
  listShifts(propId?: number, status?: string, limit: number = 50) {
    let params = new HttpParams();
    if (propId) params = params.set('prop_id', String(propId));
    if (status) params = params.set('status', status);
    if (limit) params = params.set('limit', String(limit));
    return this.http.get<{ items: ShiftInfo[]; total: number }>(
      '/api/reception/shifts',
      { params, withCredentials: true },
    );
  }
}
