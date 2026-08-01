import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { DatePipe, CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { ShiftsApiService, ShiftInfo } from '../../services/shifts-api.service';

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

}
