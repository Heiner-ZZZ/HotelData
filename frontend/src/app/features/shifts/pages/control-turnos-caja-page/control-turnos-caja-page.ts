import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DatePipe, CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { ShiftsApiService, ShiftInfo, ShiftCloseSummary, DepositRecord, PaymentBreakdown, CASH_DEPOSIT_METHODS } from '../../services/shifts-api.service';

@Component({
  selector: 'app-control-turnos-caja',
  imports: [DatePipe, CurrencyPipe, FormsModule, PropertySelectorComponent],
  templateUrl: './control-turnos-caja-page.html',
  styleUrl: './control-turnos-caja-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ControlTurnosCajaPageComponent {
  private readonly api = inject(ShiftsApiService);
  private readonly propCtx = inject(PropertyContextService);
  private readonly toast = inject(ToastService);

  readonly selectedPropId = this.propCtx.currentPropId;
  readonly selectedLabel = signal('');

  // ── State ──
  readonly loading = signal(true);
  readonly shift = signal<ShiftInfo | null>(null);
  readonly shiftTypeLabels = signal<Record<string, string>>({});
  readonly lastClosedShift = signal<ShiftInfo | null>(null);

  // Shift open form
  readonly showOpenForm = signal(false);
  readonly openShiftType = signal('morning');
  readonly openEmployee = signal('');
  readonly openCashInitial = signal<number | null>(null);

  // Close shift
  readonly showCloseModal = signal(false);
  readonly closeCashCounted = signal(0);
  readonly closeCashLeft = signal(0);
  readonly closeDeposits = signal<DepositRecord[]>([]);
  readonly closingShift = signal(false);
  readonly closeClosingNotes = signal('');

  // Deposit modal
  readonly showDepositModal = signal(false);
  readonly depositAmount = signal(0);
  readonly depositMethod = signal('bank');
  readonly depositNotes = signal('');

  // Close summary (after successful close)
  readonly closeSummary = signal<ShiftCloseSummary | null>(null);

  // ── Computed: payment method totals for display ──
  readonly paymentBreakdown = computed<PaymentBreakdown>(() => {
    const s = this.shift();
    if (!s) return { cash: 0, card: 0, transfer: 0, other: 0, total: 0 };

    // If shift already has a calculated breakdown, use it
    if (s.payment_breakdown) return s.payment_breakdown;

    // Otherwise calculate from transactions
    const cash = s.transactions
      .filter((t: { type: string; payment_method?: string; amount?: number }) =>
        (t.type === 'check_out' || t.type === 'payment') &&
        (t.payment_method || '').toLowerCase().trim() === 'cash')
      .reduce((sum: number, t: { amount?: number }) => sum + (t.amount || 0), 0);
    const card = s.transactions
      .filter((t: { type: string; payment_method?: string; amount?: number }) =>
        (t.type === 'check_out' || t.type === 'payment') &&
        (t.payment_method || '').toLowerCase().trim() === 'card')
      .reduce((sum: number, t: { amount?: number }) => sum + (t.amount || 0), 0);
    const transfer = s.transactions
      .filter((t: { type: string; payment_method?: string; amount?: number }) =>
        (t.type === 'check_out' || t.type === 'payment') &&
        (t.payment_method || '').toLowerCase().trim() === 'transfer')
      .reduce((sum: number, t: { amount?: number }) => sum + (t.amount || 0), 0);
    const other = s.transactions
      .filter((t: { type: string; payment_method?: string; amount?: number }) =>
        (t.type === 'check_out' || t.type === 'payment') &&
        !['cash', 'card', 'transfer'].includes((t.payment_method || '').toLowerCase().trim()))
      .reduce((sum: number, t: { amount?: number }) => sum + (t.amount || 0), 0);
    const total = +(cash + card + transfer + other).toFixed(2);

    return {
      cash: +cash.toFixed(2),
      card: +card.toFixed(2),
      transfer: +transfer.toFixed(2),
      other: +other.toFixed(2),
      total,
    };
  });

  /** Total esperado en caja = fondo inicial + cobros en efectivo */
  readonly totalEsperado = computed(() => {
    const ci = this.shift()?.cash_initial ?? 0;
    return +(ci + this.paymentBreakdown().cash).toFixed(2);
  });

  /** Total de depósitos del cierre */
  readonly depositTotal = computed(() => {
    return this.closeDeposits().reduce((sum, d) => sum + (d.amount || 0), 0);
  });

  /** Total de depósitos en efectivo (solo estos reducen la caja física) */
  readonly cashDepositTotal = computed(() => {
    return this.closeDeposits()
      .filter(d => CASH_DEPOSIT_METHODS.includes(String(d.method || '').toLowerCase()))
      .reduce((sum, d) => sum + (d.amount || 0), 0);
  });

  /** Efectivo que quedará en caja (contado - depósitos en efectivo) */
  readonly computedCashLeft = computed(() => {
    return +(this.closeCashCounted() - this.cashDepositTotal()).toFixed(2);
  });

  readonly saldoReal = signal(0);

  readonly diferencia = computed(() => {
    const real = this.saldoReal();
    const esperado = this.totalEsperado();
    if (real === 0 && esperado === 0) return 0;
    return +(real - esperado).toFixed(2);
  });

  readonly diferenciaClass = computed(() => {
    const d = this.diferencia();
    if (d < 0) return 'negative';
    if (d > 0) return 'positive';
    return 'zero';
  });

  // ── Init ──

  constructor() {
    this.loadShift();
  }

  // ── Data loading ──

  private loadShift(): void {
    const propId = this.selectedPropId();
    if (!propId) {
      this.loading.set(false);
      this.shift.set(null);
      return;
    }

    this.loading.set(true);
    this.api.getActiveShift(propId).subscribe({
      next: (res: { shift: ShiftInfo | null; shift_type_labels: Record<string, string> }) => {
        this.shift.set(res.shift);
        this.shiftTypeLabels.set(res.shift_type_labels);
        if (res.shift) {
          this.saldoReal.set(res.shift.cash_initial || 0);
        }
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.shift.set(null);
      },
    });
  }

  onPropSelected(event: { propId: number; label: string }): void {
    this.selectedLabel.set(event.label || `Propiedad #${event.propId}`);
    if (event.propId) {
      this.propCtx.setProperty(event.propId, event.label);
    } else {
      this.propCtx.clear();
    }
    this.loadShift();
  }

  // ── Open shift ──

  openOpenForm(): void {
    const propId = this.selectedPropId();
    if (!propId) return;

    this.showOpenForm.set(true);
    this.openShiftType.set('morning');
    this.openEmployee.set('');
    this.openCashInitial.set(null);

    // Fetch last closed shift to show carry-over suggestion
    this.api.listShifts(propId, 'closed', 1).subscribe({
      next: (res) => {
        const last = res.items[0] ?? null;
        this.lastClosedShift.set(last);
        if (last && last.cash_left !== null && last.cash_left !== undefined) {
          this.openCashInitial.set(last.cash_left);
        }
      },
      error: () => this.lastClosedShift.set(null),
    });
  }

  cancelOpenForm(): void {
    this.showOpenForm.set(false);
    this.lastClosedShift.set(null);
  }

  confirmOpenShift(): void {
    const propId = this.selectedPropId();
    if (!propId || !this.openEmployee().trim()) return;

    const cashInitial = this.openCashInitial();
    this.api.openShift(propId, this.openShiftType(), this.openEmployee().trim(), cashInitial ?? undefined).subscribe({
      next: (res: { message: string; shift: ShiftInfo }) => {
        this.toast.success(res.message);
        this.showOpenForm.set(false);
        this.shift.set(res.shift);
        this.saldoReal.set(res.shift.cash_initial || 0);
        this.lastClosedShift.set(null);
      },
      error: (err: any) => {
        this.toast.error(err?.error?.detail || 'Error al abrir turno');
      },
    });
  }

  // ── Close shift ──

  openCloseModal(): void {
    this.showCloseModal.set(true);
    this.closeCashCounted.set(0);
    this.closeDeposits.set([]);
    this.closeClosingNotes.set('');
    this.closingShift.set(false);
    // Default cash_left to the computed suggestion (will be updated after
    // deposits change via the computedCashLeft signal).
    this.closeCashLeft.set(this.computedCashLeft());
  }

  cancelClose(): void {
    this.showCloseModal.set(false);
    this.closeSummary.set(null);
  }

  confirmCloseShift(): void {
    const s = this.shift();
    if (!s) return;

    this.closingShift.set(true);
    this.api.closeShift(
      s.id,
      this.closeCashCounted(),
      this.closeCashLeft() || this.computedCashLeft(),
      this.closeDeposits().length > 0 ? this.closeDeposits() : undefined,
      this.closeClosingNotes(),
    ).subscribe({
      next: (res: { message: string; summary: ShiftCloseSummary }) => {
        this.closingShift.set(false);
        this.closeSummary.set(res.summary);
        this.shift.set(null);
        this.toast.success(res.message);

        // Auto-hide summary after a few seconds
        setTimeout(() => {
          this.closeSummary.set(null);
          this.showCloseModal.set(false);
        }, 8000);
      },
      error: (err: any) => {
        this.closingShift.set(false);
        this.toast.error(err?.error?.detail || 'Error al cerrar turno');
      },
    });
  }

  // ── Deposits ──

  openDepositModal(): void {
    this.showDepositModal.set(true);
    this.depositAmount.set(0);
    this.depositMethod.set('bank');
    this.depositNotes.set('');
  }

  cancelDeposit(): void {
    this.showDepositModal.set(false);
  }

  addDeposit(): void {
    const amount = this.depositAmount();
    if (amount <= 0) return;
    const deposits = this.closeDeposits();
    deposits.push({
      amount,
      method: this.depositMethod(),
      notes: this.depositNotes(),
    });
    this.closeDeposits.set([...deposits]);
    this.showDepositModal.set(false);
    this.toast.success(`Depósito de $${amount.toFixed(2)} agregado al cierre`);
  }

  removeDeposit(index: number): void {
    const deposits = this.closeDeposits();
    deposits.splice(index, 1);
    this.closeDeposits.set([...deposits]);
  }

  // ── Helpers ──

  getBadgeClass(method: string): string {
    switch (method.toLowerCase()) {
      case 'cash': case 'efectivo': return 'badge-cash';
      case 'card': case 'tarjeta': return 'badge-card';
      case 'transfer': case 'transf': return 'badge-transfer';
      default: return 'badge-other';
    }
  }

  getBadgeLabel(method: string): string {
    switch (method.toLowerCase()) {
      case 'cash': return 'EFECTIVO';
      case 'card': return 'TARJETA';
      case 'transfer': return 'TRANSF';
      default: return method.toUpperCase();
    }
  }

  getShiftTypeLabel(type: string): string {
    return this.shiftTypeLabels()[type] || type;
  }

  /** Duration string from start to now */
  get duration(): string {
    const s = this.shift();
    if (!s?.start_time) return '—';
    const start = new Date(s.start_time);
    const now = new Date();
    const diffMs = now.getTime() - start.getTime();
    const hrs = Math.floor(diffMs / 3600000);
    const mins = Math.floor((diffMs % 3600000) / 60000);
    return `${hrs}h ${mins}m`;
  }
}
