import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { httpResource } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import type { CheckInRowViewModel, CheckInsViewModel } from '../../models/check-ins.model';
import type { CheckInsDto } from '../../models/check-ins.dto';
import { CheckInsApiService, type DateHistoryEntry } from '../../services/check-ins-api.service';
import { type OperationalStatsResponse } from '../../../../shared/services/kpi-api.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { mapCheckIns } from '../../mappers/check-ins.mapper';

function todayIso(): string {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

function shiftDate(iso: string, days: number): string {
  const d = new Date(iso + 'T12:00:00');
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

@Component({
  selector: 'app-check-ins-page',
  imports: [DatePipe, KpiChartComponent, ReactiveFormsModule, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, RouterLink],
  templateUrl: './check-ins-page.html',
  styleUrl: './check-ins-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CheckInsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(CheckInsApiService);
  private readonly formBuilder = inject(FormBuilder);
  readonly propertyCtx = inject(PropertyContextService);

  // ── KPI: Operational stats ──
  readonly opStatsResource = httpResource<OperationalStatsResponse>(() => '/api/kpi/operational-stats');
  readonly opStats = computed(() => this.opStatsResource.value() ?? null);

  readonly dateForm = this.formBuilder.nonNullable.group({
    operationDate: [todayIso(), Validators.required],
  });

  // ── Route params as signals ──
  private readonly routeParams = toSignal(
    this.route.queryParamMap.pipe(
      map((params) => ({
        propId: Number(params.get('prop_id') ?? '0'),
        operationDate: params.get('date') || todayIso(),
      })),
      distinctUntilChanged((a, b) => a.propId === b.propId && a.operationDate === b.operationDate),
    ),
    { initialValue: { propId: 0, operationDate: todayIso() } }
  );

  // ── Declarative data fetching ──
  readonly checkInsResource = httpResource<CheckInsViewModel>(() => {
    const { propId, operationDate } = this.routeParams();
    return `/api/management/check-ins?date=${operationDate}${propId ? `&prop_id=${propId}` : ''}`;
  }, {
    parse: (res) => mapCheckIns(res as CheckInsDto),
  });

  // ── Derived state ──
  readonly viewState = computed(() => {
    if (this.checkInsResource.isLoading()) return 'loading' as const;
    if (this.checkInsResource.error()) return 'error' as const;
    const vm = this.checkInsResource.value();
    if (!vm) return 'loading' as const;
    return vm.items.length ? 'success' as const : 'empty' as const;
  });

  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly operationDate = signal(todayIso());

  readonly selectedPropId = computed(() => this.routeParams().propId);
  readonly selectedPropName = computed(() => {
    const vm = this.checkInsResource.value();
    const pid = this.selectedPropId();
    if (!vm) return '';
    const opt = vm.propertyOptions.find(p => p.propId === pid);
    return opt?.label ?? '';
  });
  readonly filter = signal('');
  readonly propertyOptions = computed(() => this.checkInsResource.value()?.propertyOptions ?? []);
  readonly dropdownOpen = signal(false);

  // Edit check-in date/time modal
  readonly editTarget = signal<{ bookingId: string; checkInDate: string; checkInTime: string } | null>(null);
  readonly editDateValue = signal('');
  readonly editTimeValue = signal('');
  readonly editSaving = signal(false);
  readonly editError = signal('');

  // More menu (⋮)
  readonly showMenu = signal(false);

  // Date history
  readonly showHistory = signal(false);
  readonly historyDatesResource = httpResource<DateHistoryEntry[]>(() => {
    if (!this.showHistory()) return undefined;
    const propId = this.selectedPropId();
    return propId ? `/api/management/check-ins/dates?prop_id=${propId}` : '/api/management/check-ins/dates';
  });
  readonly historyDates = computed(() => this.historyDatesResource.value() ?? []);
  readonly historyLoading = computed(() => this.historyDatesResource.isLoading());
  readonly historyGlobal = signal(false);

  readonly filteredOptions = computed(() => {
    const q = this.filter().toLowerCase().trim();
    const opts = this.propertyOptions();
    return q ? opts.filter(p => p.label.toLowerCase().includes(q)) : opts;
  });

  constructor() {
    // Auto-carga en modo single-hotel: si no hay prop_id en URL pero el contexto
    // está ready, navegar con el propId del contexto
    effect(() => {
      if (this.propertyCtx.ready() && this.propertyCtx.singleHotelMode()) {
        const propId = this.propertyCtx.currentPropId();
        if (propId && !this.routeParams().propId) {
          void this.router.navigate([], {
            relativeTo: this.route,
            queryParams: { prop_id: propId, date: this.operationDate() },
          });
        }
      }
    });
  }

  navigateDate(days: number): void {
    const current = this.operationDate();
    const next = shiftDate(current, days);
    this.operationDate.set(next);
    this.applyFilters();
  }

  goToday(): void {
    this.operationDate.set(todayIso());
    this.applyFilters();
  }

  applyFilters(): void {
    const date = this.operationDate();
    const propId = this.selectedPropId();
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: propId || null, date },
    });
  }

  selectProperty(propId: number, label: string): void {
    this.dropdownOpen.set(false);
    if (propId) this.filter.set(label);
    else this.filter.set('');
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: propId || null, date: this.operationDate() },
    });
  }

  clearProperty(): void {
    this.dropdownOpen.set(false);
    this.filter.set('');
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: null, date: this.operationDate() },
    });
  }

  toggleMenu(): void {
    this.showMenu.update(v => !v);
  }

  closeMenu(): void {
    this.showMenu.set(false);
  }

  openHistory(): void {
    this.closeMenu();
    this.historyGlobal.set(!this.selectedPropId());
    this.showHistory.set(true);
    this.errorMessage.set('');
  }

  closeHistory(): void {
    this.showHistory.set(false);
    this.errorMessage.set('');
  }

  goToDate(date: string, entryPropId?: number): void {
    this.closeHistory();
    this.operationDate.set(date);
    if (entryPropId) {
      const opt = this.propertyOptions().find(p => p.propId === entryPropId);
      if (opt) {
        this.applyFilters();
      }
    }
    this.applyFilters();
  }

  toggleDropdown(): void {
    this.dropdownOpen.update(v => !v);
  }

  closeDropdown(): void {
    setTimeout(() => this.dropdownOpen.set(false), 200);
  }

  completeCheckIn(bookingId: string): void {
    const current = this.checkInsResource.value();
    if (!current) return;
    this.api.completeCheckIn(bookingId).subscribe({
      next: () => {
        this.message.set('Check-in completado');
        this.errorMessage.set('');
      },
      error: (err: ApiError) => {
        this.errorMessage.set(err.message || 'Error al completar check-in.');
        this.message.set('');
      }
    });
  }

  // ── Edit check-in date/time ──

  openEditDateTime(item: CheckInRowViewModel) {
    this.editTarget.set({
      bookingId: item.bookingId,
      checkInDate: item.checkInDate,
      checkInTime: item.checkInTime || '',
    });
    this.editDateValue.set(item.checkInDate);
    this.editTimeValue.set(item.checkInTime || '');
    this.editError.set('');
  }

  closeEditDateTime() {
    this.editTarget.set(null);
    this.editDateValue.set('');
    this.editTimeValue.set('');
    this.editSaving.set(false);
    this.editError.set('');
  }

  saveEditDateTime() {
    const target = this.editTarget();
    if (!target) return;

    const newDate = this.editDateValue();
    const newTime = this.editTimeValue();

    if (!newDate) {
      this.editError.set('La fecha es obligatoria.');
      return;
    }

    this.editSaving.set(true);
    this.editError.set('');

    const dateChanged = newDate !== target.checkInDate;
    const timeChanged = newTime !== target.checkInTime;

    if (!dateChanged && !timeChanged) {
      this.closeEditDateTime();
      return;
    }

    this.api.updateCheckInDateTime(
      target.bookingId,
      dateChanged ? newDate : undefined,
      timeChanged ? newTime : undefined,
    ).subscribe({
      next: () => {
        this.editSaving.set(false);
        this.closeEditDateTime();
        this.message.set('Fecha/hora de check-in actualizada.');
        this.errorMessage.set('');
        // Refresh the view
        this.applyFilters();
      },
      error: (err: any) => {
        this.editSaving.set(false);
        this.editError.set(err?.error?.detail || err?.message || 'Error al actualizar fecha/hora.');
      },
    });
  }
}
