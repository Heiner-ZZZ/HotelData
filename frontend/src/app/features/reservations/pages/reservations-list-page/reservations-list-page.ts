import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ReservationStats, ReservationsListViewModel } from '../../models/reservations.model';
import { ReservationsApiService, type DateHistoryEntry } from '../../services/reservations-api.service';
import { ReceptionCalendarComponent } from '../../components/reception-calendar/reception-calendar';

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
  selector: 'app-reservations-list-page',
  imports: [DatePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, PropertySelectorComponent, ReactiveFormsModule, ReceptionCalendarComponent, RouterLink],
  templateUrl: './reservations-list-page.html',
  styleUrl: './reservations-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ReservationsListPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly reservationsApi = inject(ReservationsApiService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly propertyCtx = inject(PropertyContextService);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<ReservationsListViewModel | null>(null);
  readonly stats = signal<ReservationStats | null>(null);
  readonly statsLoading = signal(false);
  readonly exporting = signal(false);

  readonly isStaff = computed(() => {
    const role = this.authService.currentUser()?.primaryRole;
    return role ? ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'].includes(role) : false;
  });

  readonly isClient = computed(() => {
    const role = this.authService.currentUser()?.primaryRole;
    return !role || role === 'cliente';
  });

  /** View toggle: 'calendar' (default) or 'list'. */
  readonly viewMode = signal<'list' | 'calendar'>('calendar');
  /** Property ID for hotel selection (required before showing any view). */
  readonly calendarPropId = signal(0);
  readonly calendarPropLabel = signal('');

  /** True when a hotel has been selected via the property selector. */
  readonly hotelSelected = computed(() => this.calendarPropId() > 0);

  readonly dateForm = this.formBuilder.nonNullable.group({
    createdDate: ['', [Validators.required]]
  });

  // Current date filter (to sync between switchMap and next)
  readonly currentDateFilter = signal('');
  readonly currentStatusFilter = signal('');

  setViewMode(mode: 'list' | 'calendar') {
    this.viewMode.set(mode);
  }

  onCalendarPropSelected(event: { propId: number; label: string }) {
    this.calendarPropId.set(event.propId);
    this.calendarPropLabel.set(event.label);
    if (event.propId) {
      this.propertyCtx.setProperty(event.propId, event.label || `Propiedad #${event.propId}`);
    } else {
      this.propertyCtx.clear();
    }
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: event.propId || null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  onCalendarReservationClick(reservation: any) {
    // Could navigate to reservation detail or keep modal open
  }

  // Inline confirm/reject
  readonly confirmingId = signal<string | null>(null);
  readonly rejectingId = signal<string | null>(null);
  readonly successMessage = signal('');

  // More menu (⋮)
  readonly showMenu = signal(false);

  // Date history
  readonly showHistory = signal(false);
  readonly historyDates = signal<DateHistoryEntry[]>([]);
  readonly historyLoading = signal(false);

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map((params) => ({
          page: Number(params.get('page') ?? '1'),
          createdDate: params.get('date') || '',
          status: params.get('status') || '',
          propId: Number(params.get('prop_id') ?? '0'),
        })),
        distinctUntilChanged((a, b) => a.page === b.page && a.createdDate === b.createdDate && a.status === b.status && a.propId === b.propId),
        switchMap(({ page, createdDate, status, propId }) => {
          this.viewState.set('loading');
          this.currentDateFilter.set(createdDate || '');
          this.currentStatusFilter.set(status || '');
          if (propId) this.calendarPropId.set(propId);
          return this.reservationsApi.getReservations(page, createdDate || undefined, status || undefined, propId || undefined);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (data) => {
          this.data.set(data);
          this.dateForm.controls.createdDate.setValue(this.currentDateFilter(), { emitEvent: false });
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error')
      });

    this.loadStats();
  }

  private loadStats() {
    this.statsLoading.set(true);
    this.reservationsApi
      .getStats()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (stats) => {
          this.stats.set(stats);
          this.statsLoading.set(false);
        },
        error: () => this.statsLoading.set(false)
      });
  }

  exportCsv() {
    if (this.exporting()) return;
    this.exporting.set(true);
    this.reservationsApi
      .exportCsv()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `reservas_export_${new Date().toISOString().slice(0, 10)}.csv`;
          a.click();
          window.URL.revokeObjectURL(url);
          this.exporting.set(false);
        },
        error: () => this.exporting.set(false)
      });
  }

  navigateDate(days: number): void {
    const current = this.dateForm.controls.createdDate.value || todayIso();
    this.dateForm.controls.createdDate.setValue(shiftDate(current, days));
    this.applyFilter();
  }

  goToday(): void {
    this.dateForm.controls.createdDate.setValue(todayIso());
    this.applyFilter();
  }

  clearDateFilter(): void {
    this.dateForm.controls.createdDate.setValue('');
    this.applyFilter();
  }

  filterPending(): void {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { status: 'pending', date: null, page: null }
    });
  }

  clearStatusFilter(): void {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { status: null, page: null }
    });
  }

  applyFilter(): void {
    const createdDate = this.dateForm.controls.createdDate.value;
    const status = this.currentStatusFilter();
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { status: status || null, date: createdDate || null, page: null }
    });
  }

  goToPage(page: number) {
    const createdDate = this.dateForm.controls.createdDate.value;
    const status = this.currentStatusFilter();
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { status: status || null, date: createdDate || null, page: page > 1 ? page : null }
    });
  }

  confirmReservation(bookingId: string): void {
    if (this.confirmingId()) return;
    this.confirmingId.set(bookingId);
    this.successMessage.set('');
    this.reservationsApi.confirmReservation(bookingId).pipe(
      switchMap(() => {
        const date = this.currentDateFilter();
        const status = this.currentStatusFilter();
        return this.reservationsApi.getReservations(1, date || undefined, status || undefined);
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (data) => {
        this.data.set(data);
        this.confirmingId.set(null);
        this.successMessage.set('Reserva confirmada');
        this.loadStats();
        setTimeout(() => this.successMessage.set(''), 3000);
      },
      error: () => {
        this.confirmingId.set(null);
      }
    });
  }

  rejectReservation(bookingId: string): void {
    if (this.rejectingId()) return;
    this.rejectingId.set(bookingId);
    this.successMessage.set('');
    this.reservationsApi.rejectReservation(bookingId).pipe(
      switchMap(() => {
        const date = this.currentDateFilter();
        const status = this.currentStatusFilter();
        return this.reservationsApi.getReservations(1, date || undefined, status || undefined);
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (data) => {
        this.data.set(data);
        this.rejectingId.set(null);
        this.successMessage.set('Reserva rechazada');
        this.loadStats();
        setTimeout(() => this.successMessage.set(''), 3000);
      },
      error: () => {
        this.rejectingId.set(null);
      }
    });
  }

  toggleMenu(): void {
    this.showMenu.update(v => !v);
  }

  closeMenu(): void {
    this.showMenu.set(false);
  }

  openHistory(): void {
    if (this.historyLoading()) return;
    this.closeMenu();
    this.showHistory.set(true);
    this.historyLoading.set(true);
    this.reservationsApi.getReservationDates().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (dates) => {
        this.historyDates.set(dates);
        this.historyLoading.set(false);
      },
      error: () => {
        this.historyLoading.set(false);
      }
    });
  }

  closeHistory(): void {
    this.showHistory.set(false);
    this.historyDates.set([]);
  }

  goToDate(date: string): void {
    this.closeHistory();
    this.dateForm.controls.createdDate.setValue(date);
    this.applyFilter();
  }
}
