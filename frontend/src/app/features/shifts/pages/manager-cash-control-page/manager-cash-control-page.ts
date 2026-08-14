import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { DatePipe, CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { ShiftsApiService, EmployeeSummary, ShiftInfo, ShiftPayment } from '../../services/shifts-api.service';

@Component({
  selector: 'app-manager-cash-control-page',
  imports: [DatePipe, CurrencyPipe, FormsModule, PropertySelectorComponent],
  templateUrl: './manager-cash-control-page.html',
  styleUrl: './manager-cash-control-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ManagerCashControlPageComponent {
  private readonly api = inject(ShiftsApiService);
  private readonly propCtx = inject(PropertyContextService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);

  readonly selectedPropId = this.propCtx.currentPropId;
  readonly selectedLabel = signal('');

  readonly loading = signal(false);
  readonly shifts = signal<ShiftInfo[]>([]);
  /** Empty dates mean "all available history"; the API still caps the result at 200. */
  readonly startDate = signal<string>('');
  readonly endDate = signal<string>('');
  readonly selectedShift = signal<ShiftInfo | null>(null);

  readonly totalOverShort = computed(() => {
    return this.shifts().reduce((sum, s) => sum + (s.cash_over_short ?? 0), 0);
  });

  readonly totalCounted = computed(() => {
    return this.shifts().reduce((sum, s) => sum + (s.cash_counted ?? 0), 0);
  });

  readonly totalExpected = computed(() => {
    return this.shifts().reduce((sum, s) => sum + (s.cash_expected ?? s.cash_initial ?? 0), 0);
  });

  constructor() {
    effect(() => {
      const propId = this.selectedPropId();
      if (propId) {
        this.loadShifts();
      } else {
        this.shifts.set([]);
      }
    });
  }

  onPropSelected(event: { propId: number; label: string }): void {
    this.selectedLabel.set(event.label || `Propiedad #${event.propId}`);
    if (event.propId) {
      this.propCtx.setProperty(event.propId, event.label);
    } else {
      this.propCtx.clear();
    }
    this.loadShifts();
  }

  /** Gerencia: all open shifts across the chain (forgotten-shift detection). */
  openOpenShiftsOverview(): void {
    void this.router.navigate(['/management/shifts/open-shifts']);
  }

  loadShifts(): void {
    const propId = this.selectedPropId();
    if (!propId) return;

    this.loading.set(true);
    this.api.listShiftsForCashControl(propId, this.startDate(), this.endDate(), 200).subscribe({
      next: (res) => {
        this.shifts.set(res.items);
        this.loading.set(false);
      },
      error: (err: { error?: { detail?: unknown } }) => {
        const detail = err?.error?.detail;
        this.toast.error(typeof detail === 'string' ? detail : 'Error al cargar control de cajas');
        this.loading.set(false);
      },
    });
  }

  onDateChange(): void {
    this.loadShifts();
  }

  selectShift(shift: ShiftInfo): void {
    this.selectedShift.set(shift);
  }

  closeDetail(): void {
    this.selectedShift.set(null);
  }

  /** Nombre de archivo sugerido en el diálogo "Guardar como PDF".
   *
   * Los navegadores usan ``document.title`` como nombre por defecto al guardar
   * el PDF del arqueo; lo componemos con hotel + turno + empleado para que el
   * archivo se identifique solo, y lo restauramos tras imprimir.
   */
  private arqueoPrintTitle(): string {
    const shift = this.selectedShift();
    if (!shift) return 'Arqueo de caja';
    const hotel = (this.selectedLabel() || `Hotel ${shift.prop_id}`).replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '-');
    const tipo = this.shiftTypeLabel(shift.shift_type || '');
    const empleado = (shift.employee || shift.opened_by || 'sin-empleado').replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '-');
    const fecha = shift.start_time ? shift.start_time.slice(0, 10) : '';
    return ['Arqueo', hotel, tipo, empleado, fecha].filter(Boolean).join('-');
  }

  /** Print the shift close detail (arqueo) via the browser print dialog.
   *
   * The @media print stylesheet renders only the modal content as a clean
   * B/N document with the payments table and responsible cashiers, so the
   * manager can "Save as PDF" and attach it to the daily arqueo. The document
   * title is temporarily swapped for the suggested PDF filename and restored
   * right after, so the app's own title survives.
   */
  printDetail(): void {
    const originalTitle = document.title;
    document.title = this.arqueoPrintTitle();
    try {
      window.print();
    } finally {
      document.title = originalTitle;
    }
  }

  /** Per-employee totals of the selected shift (stamped vs deposited check). */
  readonly employeeSummary = computed<EmployeeSummary[]>(() => this.selectedShift()?.employee_summary ?? []);

  /** Total stamped across all cashiers of the selected shift. */
  readonly employeeSummaryTotal = computed(() => {
    return this.employeeSummary().reduce((sum, g) => sum + (g.total ?? 0), 0);
  });

  overShortClass(value: number | null | undefined): string {
    if (value === null || value === undefined) return 'zero';
    if (value < 0) return 'negative';
    if (value > 0) return 'positive';
    return 'zero';
  }

  shiftTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      morning: 'Matutino',
      afternoon: 'Vespertino',
      evening: 'Nocturno',
    };
    return labels[type] || type;
  }

  paymentMethodLabel(method: string): string {
    const labels: Record<string, string> = {
      cash: 'Efectivo',
      card: 'Tarjeta',
      credit_card: 'Tarjeta crédito',
      bank_transfer: 'Transferencia',
      simulated: 'Simulación',
      mix: 'Mixto',
    };
    return labels[method] || method || '—';
  }

  /** Etiqueta legible del tipo de transacción del turno (check-in/out, pago, cancelación). */
  transactionTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      check_in: 'Check-in',
      check_out: 'Check-out',
      payment: 'Pago',
      cancellation: 'Cancelación',
    };
    return labels[type] || type || '—';
  }

  /** Responsible cashier label: employee wins, falls back to the opener. */
  responsibleLabel(p: ShiftPayment): string | null {
    return p.shift_employee || p.shift_opened_by || null;
  }

  /** Tooltip with the shift type for full attribution. */
  responsibleTitle(p: ShiftPayment): string {
    const type = p.shift_type ? ` · ${p.shift_type}` : '';
    return p.shift_employee || p.shift_opened_by ? `Responsable del cobro${type}` : 'Sin turno asociado';
  }

}
