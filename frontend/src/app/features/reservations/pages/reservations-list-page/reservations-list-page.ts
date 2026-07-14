import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal, type WritableSignal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AgGridAngular } from 'ag-grid-angular';
import type { GridReadyEvent, GridApi } from 'ag-grid-community';
import { ModuleRegistry, AllCommunityModule, ValidationModule, themeQuartz } from 'ag-grid-community';
import { HttpClient, httpResource } from '@angular/common/http';
import { distinctUntilChanged, map } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { ReservationActionService } from '../../services/reservation-action.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';

import type { ReservationStats, ReservationsListViewModel } from '../../models/reservations.model';
import type { DateHistoryEntry } from '../../services/reservations-api.service';
import { ReceptionCalendarComponent } from '../../components/reception-calendar/reception-calendar';

import { todayIso, shiftDate } from './reservations-list-page.utils';
import { buildColumnDefs } from './reservations-list-page.columns';
import { ReservationsStatsBarComponent } from './components/reservations-stats-bar/reservations-stats-bar';
import { ReservationsFiltersBarComponent } from './components/reservations-filters-bar/reservations-filters-bar';
import { ReservationsHistoryModalComponent } from './components/reservations-history-modal/reservations-history-modal';
import { mapReservationsList, mapReservationStats } from '../../mappers/reservations.mapper';
import type { ReservationsListDto, ReservationStatsDto } from '../../models/reservations.dto';

ModuleRegistry.registerModules([AllCommunityModule, ValidationModule]);

@Component({
  selector: 'app-reservations-list-page',
  imports: [
    AgGridAngular,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
    ReactiveFormsModule,
    ReceptionCalendarComponent,
    ReservationsFiltersBarComponent,
    ReservationsHistoryModalComponent,
    ReservationsStatsBarComponent,
    RouterLink,
  ],
  templateUrl: './reservations-list-page.html',
  styleUrl: './reservations-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReservationsListPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly http = inject(HttpClient);
  private readonly formBuilder = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly actionService = inject(ReservationActionService);

  // ─── Reactive query params ───
  private readonly queryParams = toSignal(
    this.activatedRoute.queryParamMap.pipe(
      map((params) => ({
        page: Number(params.get('page') ?? '1'),
        createdDate: params.get('date') || '',
        status: params.get('status') || '',
        propId: Number(params.get('prop_id') ?? '0'),
        folio: params.get('folio') || '',
        stayStatus: params.get('stay_status') || '',
        bookingSource: params.get('booking_source') || '',
      })),
      distinctUntilChanged(
        (a, b) =>
          a.page === b.page &&
          a.createdDate === b.createdDate &&
          a.status === b.status &&
          a.propId === b.propId &&
          a.folio === b.folio &&
          a.stayStatus === b.stayStatus &&
          a.bookingSource === b.bookingSource
      )
    ),
    {
      initialValue: {
        page: 1,
        createdDate: '',
        status: '',
        propId: 0,
        folio: '',
        stayStatus: '',
        bookingSource: '',
      },
    }
  );

  readonly currentDateFilter = computed(() => this.queryParams().createdDate);
  readonly currentStatusFilter = computed(() => this.queryParams().status);
  readonly currentFolioFilter = computed(() => this.queryParams().folio);
  readonly currentStayStatusFilter = computed(() => this.queryParams().stayStatus);
  readonly currentSourceFilter = computed(() => this.queryParams().bookingSource);

  readonly isStaff = computed(() => {
    const role = this.authService.currentUser()?.primaryRole;
    return role ? ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'].includes(role) : false;
  });

  readonly isClient = computed(() => {
    const role = this.authService.currentUser()?.primaryRole;
    return !role || role === 'cliente';
  });

  // ─── AG Grid ───
  readonly theme = themeQuartz;
  readonly gridApi = signal<GridApi | null>(null);
  readonly defaultColDef = {
    resizable: true,
    sortable: true,
    suppressMovable: true,
  };
  readonly rowClassRules = {
    'row-pending': (p: any) => p.data?.status === 'pending',
  };
  readonly columnDefs = buildColumnDefs({
    onConfirm: (id, name) => this.runConfirmAction(id, name),
    onReject: (id, name) => this.runRejectAction(id, name),
    isStaff: () => this.isStaff(),
  });
  readonly getRowId = (params: any) => String(params.data?.bookingId ?? params.rowIndex);

  onGridReady(params: GridReadyEvent) {
    this.gridApi.set(params.api);
  }

  onRowClicked(params: any) {
    const row = params.data;
    if (row?.bookingId) void this.promptNavigate(row);
  }

  onCellKeyDown(params: any) {
    if (params.event?.key === 'Enter') {
      params.event.stopPropagation();
      const row = params.data;
      if (row?.bookingId) void this.promptNavigate(row);
    }
  }

  private async promptNavigate(row: any): Promise<void> {
    const price = row.totalPrice != null
      ? new Intl.NumberFormat('es-MX', { maximumFractionDigits: 0 }).format(row.totalPrice)
      : null;

    const details: string[] = [];
    if (row.folio) details.push(`Folio: ${row.folio}`);
    if (row.checkInDate && row.checkOutDate) details.push(`Fechas: ${row.checkInDate} → ${row.checkOutDate}`);
    if (price) details.push(`Total: ${price} ${row.currency || ''}`.trim());

    const ok = await this.confirmDialog.open({
      title: 'Abrir reserva',
      message: `¿Deseas ver el detalle de "${row.guestName || 'esta reserva'}"?`,
      confirmLabel: 'Entrar',
      cancelLabel: 'Cancelar',
      variant: 'default',
      details: details.length ? details : undefined,
    });
    if (ok) {
      void this.router.navigate([row.bookingId], { relativeTo: this.activatedRoute });
    }
  }

  /** View toggle: 'calendar' (default for staff) or 'list' (default for clients). */
  readonly viewMode = signal<'list' | 'calendar'>('list');
  /** Property ID for hotel selection (required before showing any view). */
  readonly calendarPropId = computed(() => this.queryParams().propId || this.propertyCtx.currentPropId() || 0);
  readonly calendarPropLabel = signal('');

  /** True when a hotel has been selected via the property selector. */
  readonly hotelSelected = computed(() => this.calendarPropId() > 0);

  readonly dateForm = this.formBuilder.nonNullable.group({
    createdDate: ['', [Validators.required]],
  });

  // ─── httpResources (DTO → ViewModel via parse) ───
  readonly reservationsResource = httpResource<ReservationsListViewModel>(() => {
    const qp = this.queryParams();
    const params = new URLSearchParams();
    params.set('page', String(qp.page));
    if (qp.createdDate) params.set('date', qp.createdDate);
    if (qp.status) params.set('status', qp.status);
    if (!this.isClient() && qp.propId) params.set('prop_id', String(qp.propId));
    if (qp.folio) params.set('folio', qp.folio);
    if (qp.stayStatus) params.set('stay_status', qp.stayStatus);
    if (qp.bookingSource) params.set('booking_source', qp.bookingSource);
    const query = params.toString();
    return query ? `/reservations?${query}` : '/reservations';
  }, {
    parse: (dto) => mapReservationsList(dto as ReservationsListDto),
  });

  readonly statsResource = httpResource<ReservationStats>(() => '/reservations/stats', {
    parse: (dto) => mapReservationStats(dto as ReservationStatsDto),
  });

  readonly historyDatesResource = httpResource<DateHistoryEntry[]>(() => {
    if (!this.showHistory()) return undefined;
    const propId = this.calendarPropId();
    const params = new URLSearchParams();
    if (propId) params.set('prop_id', String(propId));
    const query = params.toString();
    return query ? `/reservations/dates?${query}` : '/reservations/dates';
  });

  errorMessage(err: unknown): string {
    return (err as { message?: string })?.message || 'Intenta nuevamente o revisa la conectividad con la API.';
  }

  // Inline confirm/reject
  readonly confirmingId = signal<string | null>(null);
  readonly rejectingId = signal<string | null>(null);
  readonly successMessage = signal('');

  // More menu (⋮)
  readonly showMenu = signal(false);
  readonly showHistory = signal(false);

  readonly exporting = signal(false);

  constructor() {
    // Sync date form with URL query params reactively
    effect(() => {
      const date = this.currentDateFilter();
      this.dateForm.controls.createdDate.setValue(date, { emitEvent: false });
    });
  }

  setViewMode(mode: 'list' | 'calendar') {
    this.viewMode.set(mode);
  }

  onCalendarPropSelected(event: { propId: number; label: string }) {
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

  applyFilter(overrides: { folio?: string; stayStatus?: string; source?: string; status?: string; createdDate?: string } = {}): void {
    const createdDate = overrides.createdDate ?? this.dateForm.controls.createdDate.value;
    const status = overrides.status ?? this.currentStatusFilter();
    const folio = overrides.folio ?? this.currentFolioFilter();
    const stayStatus = overrides.stayStatus ?? this.currentStayStatusFilter();
    const source = overrides.source ?? this.currentSourceFilter();
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: {
        status: status || null,
        date: createdDate || null,
        folio: folio || null,
        stay_status: stayStatus || null,
        booking_source: source || null,
        page: null,
      },
      queryParamsHandling: 'merge',
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
      queryParams: { status: 'pending', date: null, page: null },
    });
  }

  goToPage(page: number) {
    const createdDate = this.dateForm.controls.createdDate.value;
    const status = this.currentStatusFilter();
    const folio = this.currentFolioFilter();
    const stayStatus = this.currentStayStatusFilter();
    const source = this.currentSourceFilter();
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: {
        status: status || null,
        date: createdDate || null,
        folio: folio || null,
        stay_status: stayStatus || null,
        booking_source: source || null,
        page: page > 1 ? page : null,
      },
    });
  }

  onFolioSearch(value: string): void {
    this.applyFilter({ folio: value });
  }

  onStayStatusFilter(value: string): void {
    this.applyFilter({ stayStatus: value });
  }

  onSourceFilter(value: string): void {
    this.applyFilter({ source: value });
  }

  hasActiveFilters(): boolean {
    return !!(this.currentDateFilter() || this.currentStatusFilter() || this.currentFolioFilter() || this.currentStayStatusFilter() || this.currentSourceFilter());
  }

  clearAllFilters(): void {
    this.dateForm.controls.createdDate.setValue('');
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: {},
    });
  }

  private runConfirmAction(bookingId: string, guestName: string): void {
    this.runAction(bookingId, guestName, 'confirm', this.confirmingId, 'Reserva confirmada');
  }

  private runRejectAction(bookingId: string, guestName: string): void {
    this.runAction(bookingId, guestName, 'reject', this.rejectingId, 'Reserva rechazada');
  }

  private runAction(
    bookingId: string,
    guestName: string,
    type: 'confirm' | 'reject',
    loadingSignal: WritableSignal<string | null>,
    successMsg: string,
  ): void {
    if (this.confirmingId() || this.rejectingId()) return;
    loadingSignal.set(bookingId);
    this.successMessage.set('');

    const serviceCall =
      type === 'confirm'
        ? this.actionService.confirm({ bookingId, guestName })
        : this.actionService.reject({ bookingId, guestName });

    serviceCall.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        loadingSignal.set(null);
        this.successMessage.set(successMsg);
        this.reservationsResource.reload();
        this.statsResource.reload();
        setTimeout(() => this.successMessage.set(''), 3000);
      },
      error: () => {
        loadingSignal.set(null);
      },
    });
  }

  exportCsv() {
    if (this.exporting()) return;
    this.exporting.set(true);
    this.http
      .get('/reservations/export?format=csv', { responseType: 'blob' })
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
        error: () => this.exporting.set(false),
      });
  }

  toggleMenu(): void {
    this.showMenu.update((v) => !v);
  }

  closeMenu(): void {
    this.showMenu.set(false);
  }

  openHistory(): void {
    if (this.historyDatesResource.isLoading()) return;
    this.closeMenu();
    this.showHistory.set(true);
  }

  closeHistory(): void {
    this.showHistory.set(false);
  }

  goToDate(date: string): void {
    this.closeHistory();
    this.dateForm.controls.createdDate.setValue(date);
    this.applyFilter();
  }
}
