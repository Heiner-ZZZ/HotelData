import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, isDevMode, signal, type WritableSignal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AgGridAngular } from 'ag-grid-angular';
import type {
  CellKeyDownEvent,
  FullWidthCellKeyDownEvent,
  GetRowIdParams,
  GridReadyEvent,
  GridApi,
  RowClassParams,
  RowClickedEvent,
  SelectionChangedEvent,
} from 'ag-grid-community';
import { ModuleRegistry, AllCommunityModule, ValidationModule, themeQuartz } from 'ag-grid-community';
import { HttpClient, httpResource } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

import { ReservationsAuthService } from '../../services/reservations-auth.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { ReservationActionService } from '../../services/reservation-action.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { REPORTS_DOWNLOAD } from '../../../../core/auth/permission.constants';

import type {
  ReservationListItem,
  ReservationStats,
  ReservationsListViewModel,
} from '../../models/reservations.model';
import { mapUnpriced, ReservationsApiService } from '../../services/reservations-api.service';
import type {
  DateHistoryEntry,
  UnpricedBooking,
  UnpricedBookingRaw,
} from '../../services/reservations-api.service';
import type { ReceptionCalendarReservation } from '../../models/reception-calendar.model';
import { ReceptionTimelineComponent } from '../../components/reception-timeline/reception-timeline';

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
    ReceptionTimelineComponent,
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
  private readonly reservationsAuth = inject(ReservationsAuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly http = inject(HttpClient);
  private readonly formBuilder = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly actionService = inject(ReservationActionService);
  private readonly apiService = inject(ReservationsApiService);
  private readonly auth = inject(AuthService);

  /** Exportación CSV del listado gateada por ``reports.download``. */
  readonly canExport = computed(() => this.auth.hasPermission(REPORTS_DOWNLOAD));

  // ─── Reactive query params ───
  // Migrated from `pipe(map, distinctUntilChanged)` to Angular's signal graph.
  // `computed` with a custom 8-field `equal` comparator preserves the
  // original dedup semantics so the three httpResources + downstream
  // `currentDateFilter`/`currentStatusFilter`/... computeds re-fire only when
  // at least one filter param actually changes.
  private readonly queryParamMap = toSignal(this.activatedRoute.queryParamMap, {
    initialValue: this.activatedRoute.snapshot.queryParamMap,
  });

  private readonly queryParams = computed(
    () => {
      const p = this.queryParamMap();
      return {
        page: Number(p.get('page') ?? '1'),
        createdDate: p.get('date') || '',
        status: p.get('status') || '',
        propId: Number(p.get('prop_id') ?? '0'),
        folio: p.get('folio') || '',
        stayStatus: p.get('stay_status') || '',
        bookingSource: p.get('booking_source') || '',
        view: (p.get('view') === 'calendar' ? 'calendar' : 'list') as 'list' | 'calendar',
      };
    },
    {
      equal: (a, b) =>
        a.page === b.page &&
        a.createdDate === b.createdDate &&
        a.status === b.status &&
        a.propId === b.propId &&
        a.folio === b.folio &&
        a.stayStatus === b.stayStatus &&
        a.bookingSource === b.bookingSource &&
        a.view === b.view,
    },
  );

  readonly currentDateFilter = computed(() => this.queryParams().createdDate);
  readonly currentStatusFilter = computed(() => this.queryParams().status);
  readonly currentFolioFilter = computed(() => this.queryParams().folio);
  readonly currentStayStatusFilter = computed(() => this.queryParams().stayStatus);
  readonly currentSourceFilter = computed(() => this.queryParams().bookingSource);
  readonly activeViewTab = computed<'list' | 'timeline'>(() =>
    this.queryParams().view === 'list' ? 'list' : 'timeline',
  );

  readonly isStaff = this.reservationsAuth.isStaff;
  readonly isClient = this.reservationsAuth.isClient;

  // ─── AG Grid ───
  /**
   * ag-grid theme with semantic CSS-variable lookups so a `[data-theme="dark"]`
   * flip on the document swaps the surface/text/border tokens automatically.
   * themeQuartz (v36) without withParams() defaults to its internal light
   * constants and ignores app-level theme context.
   */
  readonly theme = themeQuartz.withParams({
    backgroundColor: 'var(--surface)',
    foregroundColor: 'var(--app-text)',
    headerBackgroundColor: 'var(--surface-soft)',
    headerTextColor: 'var(--app-text)',
    rowHoverColor: 'var(--surface-hover)',
    borderColor: 'var(--app-border)',
    cellTextColor: 'var(--app-text)',
    rowBorder: { color: 'var(--app-border)', style: 'solid', width: 1 },
    oddRowBackgroundColor: 'var(--surface-raised)',
    selectedRowBackgroundColor: 'color-mix(in srgb, var(--accent) 8%, transparent)',
  });
  readonly gridApi = signal<GridApi | null>(null);
  readonly defaultColDef = {
    resizable: true,
    sortable: true,
    suppressMovable: true,
  };
  readonly rowClassRules = {
    'row-pending': (p: RowClassParams<ReservationListItem>) => p.data?.status === 'pending',
  };
  readonly columnDefs = buildColumnDefs({
    onConfirm: (id, name) => this.runConfirmAction(id, name),
    onReject: (id, name) => this.runRejectAction(id, name),
    isStaff: () => this.isStaff(),
  });
  readonly getRowId = (params: GetRowIdParams<ReservationListItem>) => String(params.data?.bookingId ?? '');

  onGridReady(params: GridReadyEvent) {
    this.gridApi.set(params.api);
  }

  onRowClicked(params: RowClickedEvent<ReservationListItem>) {
    const row = params.data;
    if (row?.bookingId) void this.promptNavigate(row);
  }

  onCellKeyDown(
    params: CellKeyDownEvent<ReservationListItem> | FullWidthCellKeyDownEvent<ReservationListItem>,
  ): void {
    if (params.event instanceof KeyboardEvent && params.event.key === 'Enter') {
      params.event.stopPropagation();
      const row = params.data;
      if (row?.bookingId) void this.promptNavigate(row);
    }
  }

  private async promptNavigate(row: ReservationListItem): Promise<void> {
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

  /** URL remains the single source of truth for the active reception view. */
  constructor() {
    effect(() => {
      const date = this.currentDateFilter();
      this.dateForm.controls.createdDate.setValue(date, { emitEvent: false });
    });

  }

  setViewTab(tab: 'list' | 'timeline'): void {
    if (tab === 'list') {
      void this.router.navigate([], {
        relativeTo: this.activatedRoute,
        queryParams: { view: null },
        queryParamsHandling: 'merge',
      });
      return;
    }

    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: {
        view: 'calendar',
      },
      queryParamsHandling: 'merge',
    });
  }

  // ─── Bulk check-in (multi-row selection) ───
  /** Selected reservations from the ag-grid selection model. */
  readonly selectedRows = signal<ReservationListItem[]>([]);
  readonly bulkActionLoading = signal(false);
  readonly bulkActionProgress = signal<{ done: number; total: number; failures: string[] }>({
    done: 0,
    total: 0,
    failures: [],
  });

  readonly selectedRowCount = computed(() => this.selectedRows().length);

  /** Every selected row must have status='confirmed' to bulk-check-in. */
  readonly canBulkCheckIn = computed(() => {
    const rows = this.selectedRows();
    if (rows.length === 0) return false;
    return rows.every((r) => r.status === 'confirmed');
  });

  onSelectionChanged(event: SelectionChangedEvent) {
    // Freeze selection updates while a bulk action is in-flight so the
    // user can't add rows mid-loop, which would cause drift between
    // visible checkboxes and the in-flight payload.
    if (this.bulkActionLoading()) return;
    this.selectedRows.set(event.api.getSelectedRows() ?? []);
  }

  async onBulkCheckIn(): Promise<void> {
    if (!this.canBulkCheckIn() || this.bulkActionLoading()) return;

    const rows = this.selectedRows();
    const total = rows.length;
    if (total === 0) return;

    const ok = await this.confirmDialog.open({
      title: 'Check-in masivo',
      message: `Vas a registrar el check-in de ${total} reserva${total === 1 ? '' : 's'}. La operación se aplicará secuencialmente y registrará una fila en la auditoría.`,
      confirmLabel: 'Iniciar check-in',
      cancelLabel: 'Cancelar',
      variant: 'default',
    });
    if (!ok) return;

    this.bulkActionLoading.set(true);
    this.bulkActionProgress.set({ done: 0, total, failures: [] });
    this.warningMessage.set('');

    const failures: string[] = [];
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      const bookingId: string = row?.bookingId;
      if (!bookingId) {
        failures.push(`Fila sin bookingId`);
        continue;
      }
      try {
        await firstValueFrom(
          this.http.post(`/api/management/check-ins/${bookingId}/complete`, {
            payment_method: '',
          })
        );
      } catch (err: unknown) {
        // Dev visibility: log the raw error so devs see which booking +
        // HTTP status failed. The user-facing toast still gets the friendly
        // message via the failures array.
        if (isDevMode()) console.error('[reservations-list] bulk check-in failed for', bookingId, err);
        const error = err as { error?: { detail?: string }; message?: string };
        const msg = error.error?.detail || error.message || 'Error al registrar check-in';
        failures.push(`${row.guestName || bookingId}: ${msg}`);
      } finally {
        // Single signal.set call replaces the previous update-with-slice
        // pattern. O(1) per iteration (was O(N²) for N rows) and gives
        // OnPush a stable reference for change detection.
        this.bulkActionProgress.set({ done: i + 1, total, failures });
      }
    }

    this.bulkActionLoading.set(false);
    if (failures.length === 0) {
      this.successMessage.set(`Check-in masivo completado · ${total} reservas`);
    } else {
      this.successMessage.set(
        `Check-in masivo: ${total - failures.length} ok, ${failures.length} con error`
      );
      this.warningMessage.set(
        `Fallaron ${failures.length} de ${total}: ${failures.slice(0, 3).join(' · ')}${failures.length > 3 ? ' \u2026' : ''}`
      );
    }
    this.reservationsResource.reload();
    this.statsResource.reload();
    this.clearSelection();
    setTimeout(() => this.successMessage.set(''), 5000);
    setTimeout(() => this.warningMessage.set(''), 8000);
  }

  clearSelection() {
    const api = this.gridApi();
    if (api) api.deselectAll();
    this.selectedRows.set([]);
  }
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

  // ─── Banner 'reservas sin precio' (admin) ───
  // Solo staff (``reservations.update`` en el backend). Se recarga al
  // recalcular o cuando cambia la lista.
  readonly unpricedResource = httpResource<UnpricedBooking[]>(() => {
    if (!this.isStaff()) return undefined;
    return '/reservations/unpriced';
  }, {
    parse: (dto) => (dto as { items: UnpricedBookingRaw[] }).items.map(mapUnpriced),
  });

  readonly unpricedCount = computed(() => this.unpricedResource.value()?.length ?? 0);
  /** Booking_id cuyo precio se está recalculando ahora mismo. */
  readonly recalculatingId = signal<string | null>(null);

  async onRecalculatePrice(bookingId: string): Promise<void> {
    if (this.recalculatingId()) return;
    this.recalculatingId.set(bookingId);
    this.successMessage.set('');
    this.warningMessage.set('');
    try {
      const result = await firstValueFrom(this.apiService.recalculatePrice(bookingId));
      const price =
        result.total_price != null
          ? `${new Intl.NumberFormat('es-MX', { maximumFractionDigits: 2 }).format(result.total_price)} ${result.currency || 'USD'}`
          : 'sin tarifa calculable';
      this.successMessage.set(`Precio recalculado · ${bookingId} → ${price}`);
      this.reservationsResource.reload();
      this.statsResource.reload();
      this.unpricedResource.reload();
    } catch (err: unknown) {
      if (isDevMode()) console.error('[reservations-list] recalculate price failed', bookingId, err);
      this.warningMessage.set(`No se pudo recalcular ${bookingId}. Intenta nuevamente.`);
    } finally {
      this.recalculatingId.set(null);
      setTimeout(() => this.successMessage.set(''), 5000);
      setTimeout(() => this.warningMessage.set(''), 8000);
    }
  }

  readonly historyDatesResource = httpResource<DateHistoryEntry[]>(() => {
    if (!this.showHistory()) return undefined;
    const propId = this.calendarPropId();
    const params = new URLSearchParams();
    if (propId) params.set('prop_id', String(propId));
    const query = params.toString();
    return query ? `/reservations/dates?${query}` : '/reservations/dates';
  }, {
    parse: (dto) => dto as DateHistoryEntry[],
  });

  errorMessage(err: unknown): string {
    return (err as { message?: string })?.message || 'Intenta nuevamente o revisa la conectividad con la API.';
  }

  // Inline confirm/reject
  readonly confirmingId = signal<string | null>(null);
  readonly rejectingId = signal<string | null>(null);
  readonly successMessage = signal('');
  /** Warning toast for partial-failure scenarios (e.g. bulk ops with errors). */
  readonly warningMessage = signal('');

  // More menu (⋮)
  readonly showMenu = signal(false);
  readonly showHistory = signal(false);

  readonly exporting = signal(false);

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

  onCalendarReservationClick(_reservation: ReceptionCalendarReservation): void {
    // The calendar engine owns the detail panel; keep this output available
    // for future shared actions without duplicating the modal in the page.
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
      error: (err) => {
        // Dev visibility: surface the actual error so we can diagnose
        // silent confirmation/rejection failures during development.
        if (isDevMode()) console.error(`[reservations-list] ${type} action failed`, err);
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
        error: (err) => {
          // Dev visibility: surface the actual error.
          if (isDevMode()) console.error('[reservations-list] CSV export failed', err);
          this.exporting.set(false);
        },
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
