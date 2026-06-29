import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, input, output, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { ReceptionApiService, type ReceptionShift, type ShiftCloseSummary } from '../../services/reception-api.service';

export interface ShiftOpenForm {
  shift_type: 'morning' | 'afternoon' | 'evening';
  employee: string;
  cash_initial: number;
}

export interface ShiftCloseForm {
  cash_final: number;
  cash_expected: number;
  cash_difference: number;
  transaction_count: number;
}

const SHIFT_TYPE_LABELS: Record<string, string> = {
  morning: 'Matutino',
  afternoon: 'Vespertino',
  evening: 'Nocturno',
};

@Component({
  selector: 'app-shift-banner',
  imports: [FormsModule],
  templateUrl: './shift-banner.html',
  styleUrl: './shift-banner.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShiftBannerComponent {
  private readonly api = inject(ReceptionApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly Math = Math;

  readonly propId = input.required<number>();

  readonly shiftChange = output<void>();

  readonly shift = signal<ReceptionShift | null>(null);
  readonly loading = signal(false);
  readonly error = signal('');

  // ── Open shift form state ──
  readonly showOpenForm = signal(false);
  readonly openForm = signal<ShiftOpenForm>({
    shift_type: 'morning',
    employee: '',
    cash_initial: 0,
  });
  readonly opening = signal(false);

  // ── Close shift form state ──
  readonly showCloseForm = signal(false);
  readonly closeForm = signal<ShiftCloseForm>({
    cash_final: 0,
    cash_expected: 0,
    cash_difference: 0,
    transaction_count: 0,
  });
  readonly closing = signal(false);
  readonly closeSummary = signal<ShiftCloseSummary | null>(null);

  readonly hasActiveShift = computed(() => this.shift()?.status === 'open');

  readonly shiftLabel = computed(() => {
    const s = this.shift();
    if (!s) return '';
    return SHIFT_TYPE_LABELS[s.shift_type] || s.shift_type;
  });

  readonly shiftMinutes = computed(() => {
    const s = this.shift();
    if (!s?.start_time) return 0;
    const start = new Date(s.start_time).getTime();
    return Math.floor((Date.now() - start) / 60000);
  });

  readonly shiftDuration = computed(() => {
    const mins = this.shiftMinutes();
    if (mins < 60) return `${mins} min`;
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
  });

  readonly txnCount = computed(() => {
    return this.shift()?.transactions?.length ?? 0;
  });

  readonly totalCollected = computed(() => {
    return this.shift()?.total_collected ?? 0;
  });

  loadShift(): void {
    const pid = this.propId();
    if (!pid) return;
    this.loading.set(true);
    this.error.set('');
    this.api
      .getActiveShift(pid)
      .pipe(
        finalize(() => this.loading.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (res) => {
          this.shift.set(res.shift);
        },
        error: () => {
          this.error.set('Error al cargar turno activo');
        },
      });
  }

  openOpenForm(): void {
    this.openForm.set({
      shift_type: 'morning',
      employee: '',
      cash_initial: 0,
    });
    this.showOpenForm.set(true);
  }

  cancelOpen(): void {
    this.showOpenForm.set(false);
  }

  submitOpen(): void {
    const form = this.openForm();
    if (!form.employee.trim()) return;
    this.opening.set(true);
    this.error.set('');
    this.api
      .openShift({
        prop_id: this.propId(),
        shift_type: form.shift_type,
        employee: form.employee.trim(),
        cash_initial: form.cash_initial,
      })
      .pipe(
        finalize(() => this.opening.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (res) => {
          this.shift.set(res.shift);
          this.showOpenForm.set(false);
          this.shiftChange.emit();
        },
        error: (err) => {
          // Try to extract backend detail
          const detail =
            err?.error?.detail || err?.error?.message || 'Error al abrir turno';
          this.error.set(detail);
        },
      });
  }

  openCloseForm(): void {
    const s = this.shift();
    if (!s) return;
    this.closeForm.set({
      cash_final: s.cash_initial || 0,
      cash_expected: s.total_collected || 0,
      cash_difference: 0,
      transaction_count: s.transactions?.length ?? 0,
    });
    this.closeSummary.set(null);
    this.showCloseForm.set(true);
  }

  cancelClose(): void {
    this.showCloseForm.set(false);
    this.closeSummary.set(null);
  }

  previewClose(): void {
    const form = this.closeForm();
    const s = this.shift();
    if (!s) return;
    const cashExpected = s.total_collected || 0;
    const cashDiff = Math.round((form.cash_final - (s.cash_initial || 0)) * 100) / 100;
    this.closeForm.set({
      ...form,
      cash_expected: cashExpected,
      cash_difference: cashDiff,
    });
  }

  submitClose(): void {
    const s = this.shift();
    if (!s) return;
    this.closing.set(true);
    this.error.set('');
    this.api
      .closeShift(s.id, { cash_final: this.closeForm().cash_final })
      .pipe(
        finalize(() => this.closing.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (res) => {
          this.closeSummary.set(res.summary ?? null);
          this.shift.set(res.shift);
          this.shiftChange.emit();
        },
        error: (err) => {
          const detail =
            err?.error?.detail || err?.error?.message || 'Error al cerrar turno';
          this.error.set(detail);
        },
      });
  }

  dismissSummary(): void {
    this.closeSummary.set(null);
    this.showCloseForm.set(false);
  }
}
