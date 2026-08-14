import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DatePipe, CurrencyPipe } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { AuthService } from '../../../../core/auth/auth.service';
import { ShiftsApiService, ShiftInfo, ShiftCloseSummary, ActiveShiftConflict, ScheduleMismatchDetail, ScheduleBypassForbiddenDetail, DepositRecord, PaymentBreakdown, CASH_DEPOSIT_METHODS, SHIFT_TYPES, ShiftConfig, ShiftWindow } from '../../services/shifts-api.service';
import { SHIFTS_CREATE, SHIFTS_MANAGE, SHIFTS_UPDATE } from '../../../../core/auth/permission.constants';
import { getErrorMessage } from '../../../../shared/utils/http-error.util';

/** UI fallback for the per-hotel max-open-hours limit (12h = server default). */
const DEFAULT_MAX_OPEN_HOURS_UI = 12;
/** Default manager heads-up threshold (hours) shown in the config modal. */
const DEFAULT_NOTIFY_MANAGER_HOURS_UI = 8;

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
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly selectedPropId = this.propCtx.currentPropId;
  readonly selectedLabel = signal('');

  // ── State ──
  readonly loading = signal(true);
  readonly shift = signal<ShiftInfo | null>(null);
  readonly shiftTypeLabels = signal<Record<string, string>>({});
  readonly lastClosedShift = signal<ShiftInfo | null>(null);

  /**
   * Whether the current user can mutate a shift on this page.
   *
   * Combines the two back-end permission gates required to act on the
   * cashbox flow:
   * - ``shifts.create`` to open a new shift / add a force-override.
   * - ``shifts.update`` to close a shift or add a deposit.
   *
   * When this returns ``false``, the page renders only the read-only
   * history + details view (active shift info card, arqueo breakdown,
   * transaction audit). Mutation buttons (open / close / deposit) are
   * hidden from the template. The server still enforces these perms on
   * POST endpoints, so this gate is purely a UX convenience to avoid
   * 403 toasts — not a security boundary.
   */
  readonly canMutateShift = computed(() =>
    this.auth.hasPermission(SHIFTS_CREATE) ||
    this.auth.hasPermission(SHIFTS_UPDATE),
  );

  /** The history endpoint is a manager-control view protected by shifts.manage. */
  readonly canViewShiftHistory = computed(() => this.auth.hasPermission(SHIFTS_MANAGE));

  /** Manager-only: editing the per-hotel shift windows requires shifts.manage. */
  readonly canManageShifts = computed(() => this.auth.hasPermission(SHIFTS_MANAGE));

  // ── Shift-window config (per hotel) ──
  readonly shiftConfig = signal<ShiftConfig | null>(null);
  readonly showConfigModal = signal(false);
  readonly configSaving = signal(false);
  readonly configDraft = signal<Record<string, ShiftWindow>>({});
  /** Draft of the per-hotel max-open-hours limit (hours) in the config modal. */
  readonly configMaxOpenHours = signal(DEFAULT_MAX_OPEN_HOURS_UI);
  /** Draft of the per-hotel manager heads-up threshold (hours) in the modal. */
  readonly configNotifyHours = signal(DEFAULT_NOTIFY_MANAGER_HOURS_UI);
  readonly configError = signal('');

  /** True when the active shift has been open past the hotel's limit. */
  readonly shiftExpired = computed(() => !!this.shift()?.is_expired);

  /** Manager-only simplified arqueo for an expired shift. */
  readonly canEmergencyClose = computed(
    () => this.shiftExpired() && this.canManageShifts(),
  );
  readonly emergencyClose = signal(false);
  readonly emergencyReason = signal('');

  /** Select options for the open-shift form, labeled from the configured windows. */
  readonly shiftTypeOptions = computed(() =>
    SHIFT_TYPES.map(t => ({ value: t, label: this.shiftTypeLabels()[t] || t })),
  );

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

  // ── Force-open confirmation (active shift conflict, HTTP 409) ──
  readonly showForceOpenModal = signal<ActiveShiftConflict | null>(null);
  readonly forceOpening = signal(false);

  // ── Schedule mismatch modal (HTTP 422) ──
  // Triggered when ``openShift`` fails because the requested shift_type
  // doesn't match the EXPECTED block for NOW. Only users with
  // ``shifts.manage`` can flip ``scheduleBypassChecked`` and re-submit.
  readonly showScheduleMismatchModal = signal<ScheduleMismatchDetail | null>(null);
  readonly scheduleBypassChecked = signal(false);
  readonly scheduleBypassSubmitting = signal(false);

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
    this.loadShiftConfig();
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

  /** Load the per-hotel shift-window config (for the edit modal + labels). */
  private loadShiftConfig(): void {
    const propId = this.selectedPropId();
    if (!propId) return;
    this.api.getShiftConfig(propId).subscribe({
      next: (res: { config: ShiftConfig }) => {
        this.shiftConfig.set(res.config);
        // Prefer the config labels (same source the active endpoint uses),
        // so the open-shift form reflects custom windows even before the
        // active-shift response lands.
        this.shiftTypeLabels.set(res.config.labels);
      },
      error: () => {
        /* read-only best-effort — labels fall back to the active endpoint */
      },
    });
  }

  openShiftHistory(): void {
    const propId = this.selectedPropId();
    void this.router.navigate(['/management/shifts/manager-control'], {
      queryParams: propId ? { prop_id: propId } : {},
    });
  }

  /** Gerencia: all open shifts across the chain (forgotten-shift detection). */
  openOpenShiftsOverview(): void {
    void this.router.navigate(['/management/shifts/open-shifts']);
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

  // ── Shift-window config handlers ──

  openConfigModal(): void {
    const config = this.shiftConfig();
    if (!config) return;
    this.configDraft.set(JSON.parse(JSON.stringify(config.windows)));
    this.configMaxOpenHours.set(
      typeof config.max_open_hours === 'number' && config.max_open_hours > 0
        ? config.max_open_hours
        : DEFAULT_MAX_OPEN_HOURS_UI,
    );
    this.configNotifyHours.set(
      typeof config.notify_manager_hours === 'number' && config.notify_manager_hours > 0
        ? config.notify_manager_hours
        : DEFAULT_NOTIFY_MANAGER_HOURS_UI,
    );
    this.configError.set('');
    this.showConfigModal.set(true);
  }

  cancelConfigModal(): void {
    if (this.configSaving()) return;
    this.showConfigModal.set(false);
    this.configError.set('');
  }

  setConfigWindow(type: string, field: 'start' | 'end', value: string): void {
    const draft = { ...this.configDraft() };
    draft[type] = { ...(draft[type] || { start: '', end: '' }), [field]: value };
    this.configDraft.set(draft);
  }

  saveShiftConfig(): void {
    const propId = this.selectedPropId();
    const draft = this.configDraft();
    if (!propId || !draft || this.configSaving()) return;
    this.configSaving.set(true);
    this.configError.set('');
    this.api.updateShiftConfig(propId, draft, this.configMaxOpenHours(), this.configNotifyHours()).subscribe({
      next: (res: { config: ShiftConfig; message: string }) => {
        this.configSaving.set(false);
        this.shiftConfig.set(res.config);
        this.shiftTypeLabels.set(res.config.labels);
        this.showConfigModal.set(false);
        this.toast.success(res.message);
      },
      error: (err: unknown) => {
        this.configSaving.set(false);
        // The global interceptor rewraps errors as ApiError ({status, message,
        // details}); getErrorMessage covers both that and raw HttpErrorResponse
        // (test / HttpTestingController paths).
        this.configError.set(
          getErrorMessage(err) ?? 'Error al guardar la configuración de turnos',
        );
      },
    });
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
        this.showForceOpenModal.set(null);
      },
      error: (err: { status?: number; error?: { detail?: unknown } }) => {
        // 422 means the requested shift_type doesn't match the current
        // schedule window. Surface the override modal (if permitted) so
        // a gerente can authorize a bypass, or the receptionist can
        // re-open the form choosing the correct shift_type.
        if (err?.status === 422) {
          const detail = err?.error?.detail as ScheduleMismatchDetail | undefined;
          if (detail && detail.error === 'schedule_mismatch') {
            this.showScheduleMismatchModal.set(detail);
            this.scheduleBypassChecked.set(false);
            return;
          }
        }
        // 403 happens when a non-gerente tries to send bypass_schedule_check=true
        if (err?.status === 403) {
          const detail = err?.error?.detail as ScheduleBypassForbiddenDetail | undefined;
          if (detail && detail.error === 'schedule_bypass_forbidden') {
            this.toast.error(detail.message);
            return;
          }
        }
        // 409 = conflicting active shift — existing UX path
        if (err?.status === 409) {
          const detail = err?.error?.detail as ActiveShiftConflict | undefined;
          if (detail && detail.error === 'active_shift_exists') {
            this.showForceOpenModal.set(detail);
            this.toast.warning(
              detail.force_blocked_by_over_short
                ? 'Hay un turno activo con un sobrante/faltante previo sin cerrar. Primero ciérrelo manualmente.'
                : 'Hay un turno activo. Confirma cómo proceder.',
            );
            return;
          }
        }
        const fallback =
          (err?.error?.detail as string | undefined) ||
          'Error al abrir turno';
        this.toast.error(fallback);
      },
    });
  }

  // ── Schedule-mismatch modal handlers ──

  cancelScheduleMismatch(): void {
    if (this.scheduleBypassSubmitting()) return;
    this.showScheduleMismatchModal.set(null);
    this.scheduleBypassChecked.set(false);
  }

  /** Re-open the form pre-selecting the EXPECTED shift_type so the user
   *  can just confirm. Closes the mismatch modal. */
  pickExpectedShiftFromMismatch(): void {
    const m = this.showScheduleMismatchModal();
    if (!m) return;
    this.openShiftType.set(m.expected);
    this.showScheduleMismatchModal.set(null);
    this.scheduleBypassChecked.set(false);
    this.toast.info(`Cambiaste el turno al bloque correcto (${m.expected}). Confirma de nuevo.`);
  }

  /** Override: re-submit open_shift with bypass_schedule_check=true.
   *  The server enforces shifts.manage imperatively, so a frontend without
   *  the permission will simply 403 with schedule_bypass_forbidden. */
  confirmScheduleMismatchOverride(): void {
    const propId = this.selectedPropId();
    const m = this.showScheduleMismatchModal();
    if (!propId || !this.openEmployee().trim() || !m) return;
    if (!this.scheduleBypassChecked()) {
      this.toast.warning('Marca la casilla de override del gerente antes de continuar.');
      return;
    }
    this.scheduleBypassSubmitting.set(true);
    const cashInitial = this.openCashInitial();
    this.api
      .openShift(
        propId,
        this.openShiftType(),
        this.openEmployee().trim(),
        cashInitial ?? undefined,
        { bypassScheduleCheck: true },
      )
      .subscribe({
        next: (res: { message: string; shift: ShiftInfo }) => {
          this.scheduleBypassSubmitting.set(false);
          this.toast.warning(res.message + ' (horario fuera de bloque — autorizado por gerente).');
          this.showScheduleMismatchModal.set(null);
          this.scheduleBypassChecked.set(false);
          this.showOpenForm.set(false);
          this.lastClosedShift.set(null);
          this.shift.set(res.shift);
          this.saldoReal.set(res.shift.cash_initial || 0);
        },
        error: (subErr: { status?: number; error?: { detail?: unknown } }) => {
          this.scheduleBypassSubmitting.set(false);
          if (subErr?.status === 403) {
            const detail = subErr?.error?.detail as ScheduleBypassForbiddenDetail | undefined;
            this.toast.error(detail?.message ?? 'No tienes permiso para hacer override del horario.');
            // Server says no — keep the modal so the user can pick the expected shift instead.
            return;
          }
          this.toast.error((subErr?.error?.detail as string | undefined) ?? 'Error al autorizar override');
        },
      });
  }

  // ── Force-open confirmation handlers ──

  cancelForceOpen(): void {
    if (this.forceOpening()) return;
    this.showForceOpenModal.set(null);
  }

  forceOpenAnyway(): void {
    const propId = this.selectedPropId();
    const conflict = this.showForceOpenModal();
    if (!propId || !this.openEmployee().trim() || !conflict) return;
    if (conflict.force_blocked_by_over_short) {
      this.toast.error(
        'No se puede forzar el cierre: el último turno cerrado tuvo un sobrante/faltante. Ciérrelo manualmente.',
      );
      return;
    }

    this.forceOpening.set(true);
    const cashInitial = this.openCashInitial();
    this.api
      .openShift(propId, this.openShiftType(), this.openEmployee().trim(), cashInitial ?? undefined, { force: true })
      .subscribe({
        next: (res: { message: string; shift: ShiftInfo }) => {
          this.forceOpening.set(false);
          this.toast.warning(
            res.message + ' (cierre forzado del turno anterior sin reconciliación).',
          );
          this.showForceOpenModal.set(null);
          this.showOpenForm.set(false);
          this.lastClosedShift.set(null);
          this.shift.set(res.shift);
          this.saldoReal.set(res.shift.cash_initial || 0);
        },
        error: (err: { error?: { detail?: string | ActiveShiftConflict } }) => {
          this.forceOpening.set(false);
          const detail = err?.error?.detail;
          if (typeof detail === 'object' && detail !== null && 'message' in detail) {
            this.toast.error((detail as ActiveShiftConflict).message);
          } else {
            this.toast.error(typeof detail === 'string' ? detail : 'Error al forzar apertura');
          }
        },
      });
  }

  /**
   * Close the force modal and pre-fill the close-shift modal with the
   * active shift so the receptionist can properly reconcile it first.
   */
  goCloseInstead(): void {
    const conflict = this.showForceOpenModal();
    if (!conflict) return;
    // The conflict snapshot becomes our active shift signal so the
    // existing close-shift flow renders with the right data.
    this.shift.set(conflict.active_shift);
    this.saldoReal.set(conflict.active_shift.cash_initial || 0);
    this.showForceOpenModal.set(null);
    this.showOpenForm.set(false);
    this.toast.info('Cierra el turno activo con tu arqueo antes de abrir el nuevo.');
  }

  /** Computed: can the force-close button be enabled? */
  readonly canForceOpen = computed(() => {
    const c = this.showForceOpenModal();
    if (!c) return false;
    if (c.force_blocked_by_over_short) return false;
    if (this.forceOpening()) return false;
    return true;
  });

  // ── Close shift ──

  openCloseModal(): void {
    this.showCloseModal.set(true);
    this.closeCashCounted.set(0);
    this.closeDeposits.set([]);
    this.closeClosingNotes.set('');
    this.closingShift.set(false);
    this.emergencyClose.set(false);
    this.emergencyReason.set('');
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
      undefined,
      this.emergencyClose(),
      this.emergencyReason(),
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
      error: (err: { error?: { detail?: unknown } }) => {
        this.closingShift.set(false);
        const detail = err?.error?.detail;
        this.toast.error(typeof detail === 'string' ? detail : 'Error al cerrar turno');
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
