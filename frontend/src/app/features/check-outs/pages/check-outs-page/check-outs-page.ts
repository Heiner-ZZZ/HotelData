import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { httpResource } from '@angular/common/http';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { of } from 'rxjs';
import { tap } from 'rxjs/operators';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { API_CONFIG } from '../../../../core/api/api.config';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import type { CheckOutRowViewModel, CheckOutsViewModel } from '../../models/check-outs.model';
import type { CheckOutsDto } from '../../models/check-outs.dto';
import { CheckOutsApiService, type BookingCharge, type DateHistoryEntry } from '../../services/check-outs-api.service';
import type { OperationalStatsResponse } from '../../../../shared/services/kpi-api.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { mapCheckOuts } from '../../mappers/check-outs.mapper';

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
  selector: 'app-check-outs-page',
  imports: [CurrencyPipe, DatePipe, FormsModule, KpiChartComponent, ReactiveFormsModule, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, RouterLink],
  templateUrl: './check-outs-page.html',
  styleUrl: './check-outs-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CheckOutsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(CheckOutsApiService);
  private readonly http = inject(HttpClient);
  private readonly destroyRef = inject(DestroyRef);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly formBuilder = inject(FormBuilder);
  readonly propertyCtx = inject(PropertyContextService);

  // ── KPI: Operational stats ──
  readonly opStatsResource = httpResource<OperationalStatsResponse>(() => '/api/kpi/operational-stats');
  readonly opStats = computed(() => this.opStatsResource.value() ?? null);

  readonly dateForm = this.formBuilder.nonNullable.group({
    operationDate: [todayIso(), Validators.required],
  });

  // ── Route params as signals ──
  // The legacy `distinctUntilChanged(...)` operator is replaced by `computed`'s
  // `equal` option — the comparator runs after every queryParamMap emission
  // and downstream consumers (httpResource URL formula + selectedPropId /
  // selectedPropName computeds) re-evaluate only when propId or operationDate
  // actually change.
  private readonly queryParamMap = toSignal(this.route.queryParamMap, {
    initialValue: this.route.snapshot.queryParamMap,
  });

  private readonly routeParams = computed(
    () => ({
      propId: Number(this.queryParamMap().get('prop_id') ?? '0'),
      operationDate: this.queryParamMap().get('date') || todayIso(),
    }),
    {
      equal: (a, b) => a.propId === b.propId && a.operationDate === b.operationDate,
    },
  );

  // ── Declarative data fetching ──
  readonly checkOutsResource = httpResource<CheckOutsViewModel>(() => {
    const { propId, operationDate } = this.routeParams();
    return `/api/management/check-outs?date=${operationDate}${propId ? `&prop_id=${propId}` : ''}`;
  }, {
    parse: (res) => mapCheckOuts(res as CheckOutsDto),
  });

  // ── Derived state ──
  readonly viewState = computed(() => {
    if (this.checkOutsResource.isLoading()) return 'loading' as const;
    if (this.checkOutsResource.error()) return 'error' as const;
    const vm = this.checkOutsResource.value();
    if (!vm) return 'loading' as const;
    return vm.items.length ? 'success' as const : 'empty' as const;
  });

  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly Math = Math;
  protected readonly Number = Number;

  // ═══ Consumption summary modal ═══
  readonly showConsumptionModal = signal(false);
  readonly consumptionBookingId = signal('');
  readonly consumptionGuestName = signal('');
  readonly consumptionHotelLabel = signal('');
  readonly consumptionPropId = signal(0);
  readonly consumptionRoomTotal = signal(0);
  readonly confirmPending = signal(false);

  private readonly consumptionChargesCache = new Map<string, { items: BookingCharge[] }>();
  readonly consumptionChargesResource = rxResource<{ items: BookingCharge[] } | undefined, { bookingId: string; propId: number } | undefined>({
    params: () => {
      const bookingId = this.consumptionBookingId();
      const propId = this.consumptionPropId();
      return this.showConsumptionModal() && bookingId ? { bookingId, propId } : undefined;
    },
    stream: ({ params }) => {
      if (!params) return of<{ items: BookingCharge[] } | undefined>(undefined);
      const cached = this.consumptionChargesCache.get(params.bookingId);
      if (cached) return of(cached);
      return this.api.getBookingCharges(params.bookingId, params.propId).pipe(
        tap((res: { items: BookingCharge[] }) => this.consumptionChargesCache.set(params.bookingId, res)),
      );
    },
  });
  readonly consumptionCharges = computed(() => this.consumptionChargesResource.value()?.items ?? []);
  readonly consumptionLoading = computed(() => this.consumptionChargesResource.isLoading());

  // ═══ Add charge form ═══
  readonly chargeFormVisible = signal(false);
  readonly chargeConcept = signal('');
  readonly chargeAmount = signal(0);
  readonly chargeQuantity = signal(1);
  readonly chargeNote = signal('');
  readonly chargeSaving = signal(false);
  readonly chargeError = signal('');

  readonly consumptionChargesTotal = computed(() =>
    this.consumptionCharges().reduce((sum, c) => sum + (c.total || 0), 0)
  );

  readonly consumptionGrandTotal = computed(() =>
    this.consumptionRoomTotal() + this.consumptionChargesTotal()
  );

  readonly consumptionItemsCount = computed(() =>
    this.consumptionCharges().reduce((sum, c) => sum + (c.quantity || 0), 0)
  );

  // Review modal
  readonly showReviewModal = signal(false);
  readonly reviewBookingId = signal('');
  readonly reviewPropId = signal(0);
  readonly reviewGuestName = signal('');
  readonly reviewRating = signal(0);
  readonly reviewTitle = signal('');
  readonly reviewComment = signal('');
  readonly reviewSubmitting = signal(false);
  readonly reviewError = signal('');
  readonly reviewSuccess = signal(false);

  readonly operationDate = signal(todayIso());

  readonly selectedPropId = computed(() => this.routeParams().propId);
  readonly selectedPropName = computed(() => {
    const vm = this.checkOutsResource.value();
    const pid = this.selectedPropId();
    if (!vm) return '';
    const opt = vm.propertyOptions.find(p => p.propId === pid);
    return opt?.label ?? '';
  });
  readonly filter = signal('');
  readonly propertyOptions = computed(() => this.checkOutsResource.value()?.propertyOptions ?? []);
  readonly dropdownOpen = signal(false);

  // More menu (⋮)
  readonly showMenu = signal(false);

  // Date history
  readonly showHistory = signal(false);
  private readonly historyDatesCache = new Map<string, DateHistoryEntry[]>();
  readonly historyDatesResource = rxResource<DateHistoryEntry[] | undefined, { propId: number } | undefined>({
    params: () => {
      if (!this.showHistory()) return undefined;
      return { propId: this.selectedPropId() };
    },
    stream: ({ params }) => {
      if (!params) return of<DateHistoryEntry[] | undefined>(undefined);
      const key = params.propId > 0 ? String(params.propId) : 'global';
      const cached = this.historyDatesCache.get(key);
      if (cached) return of(cached);
      return this.api.getCheckOutDates(params.propId > 0 ? params.propId : undefined).pipe(
        tap((res: DateHistoryEntry[]) => this.historyDatesCache.set(key, res)),
      );
    },
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
    // Data fetching is handled declaratively via httpResource above

    // Auto-carga en modo single-hotel
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
    if (this.historyLoading()) return;
    this.closeMenu();
    const propId = this.selectedPropId();
    this.historyGlobal.set(!propId);
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
    this.applyFilters();
  }

  toggleDropdown(): void {
    this.dropdownOpen.update(v => !v);
  }

  closeDropdown(): void {
    setTimeout(() => this.dropdownOpen.set(false), 200);
  }

  openConsumptionModal(item: CheckOutRowViewModel): void {
    this.consumptionBookingId.set(item.bookingId);
    this.consumptionGuestName.set(item.guestName);
    this.consumptionHotelLabel.set(item.hotelLabel);
    this.consumptionRoomTotal.set(item.totalPrice || 0);
    this.consumptionPropId.set(item.propId);
    this.showConsumptionModal.set(true);
    this.confirmPending.set(false);
  }

  closeConsumptionModal(): void {
    this.showConsumptionModal.set(false);
    this.chargeFormVisible.set(false);
    this.chargeError.set('');
  }

  // ═══ Add / Edit Charge ═══

  toggleChargeForm(): void {
    this.chargeFormVisible.update(v => !v);
    this.chargeError.set('');
    if (this.chargeFormVisible()) {
      this.chargeConcept.set('');
      this.chargeAmount.set(0);
      this.chargeQuantity.set(1);
      this.chargeNote.set('');
    }
  }

  addCharge(): void {
    const bookingId = this.consumptionBookingId();
    const concept = this.chargeConcept().trim();
    const amount = this.chargeAmount();
    const quantity = this.chargeQuantity();
    if (!bookingId || !concept || amount <= 0) {
      this.chargeError.set('Completa el concepto y el monto del cargo.');
      return;
    }
    this.chargeSaving.set(true);
    this.chargeError.set('');

    this.api.createCharge(bookingId, this.consumptionPropId(), concept, amount, quantity, this.chargeNote()).subscribe({
      next: () => {
        this.chargeSaving.set(false);
        this.chargeError.set('');
        this.chargeFormVisible.set(false);
        this.consumptionChargesCache.delete(bookingId);
        this.consumptionChargesResource.reload();
      },
      error: (err: ApiError) => {
        this.chargeSaving.set(false);
        this.chargeError.set(
          err.message || 'No se pudo crear el cargo. Revisá el concepto y el monto e intentá de nuevo.',
        );
      },
    });
  }

  confirmCheckOut(): void {
    const bookingId = this.consumptionBookingId();
    if (!bookingId || this.confirmPending()) return;
    this.confirmPending.set(true);
    this.api.completeCheckOut(bookingId).subscribe({
      next: () => {
        this.message.set('Check-out completado correctamente');
        this.errorMessage.set('');
        this.showConsumptionModal.set(false);
        this.confirmPending.set(false);
      },
      error: (err: ApiError) => {
        this.errorMessage.set(
          err.message ||
          'No se pudo completar el check-out. Revisá el saldo y los cargos pendientes e intentá de nuevo.',
        );
        this.message.set('');
        this.confirmPending.set(false);
      },
    });
  }

  /** ═══ Review modal ═══ */

  openReviewModal(bookingId: string, propId: number, guestName: string) {
    this.reviewBookingId.set(bookingId);
    this.reviewPropId.set(propId);
    this.reviewGuestName.set(guestName);
    this.reviewRating.set(0);
    this.reviewTitle.set('');
    this.reviewComment.set('');
    this.reviewError.set('');
    this.reviewSuccess.set(false);
    this.showReviewModal.set(true);
  }

  setReviewRating(stars: number) {
    this.reviewRating.set(stars);
  }

  submitReview() {
    if (this.reviewRating() < 1) {
      this.reviewError.set('Selecciona una puntuación de 1 a 5 estrellas.');
      return;
    }
    this.reviewSubmitting.set(true);
    this.reviewError.set('');

    this.http.post(`${this.apiConfig.baseUrl}/reviews/staff`, {
      booking_id: this.reviewBookingId(),
      prop_id: this.reviewPropId(),
      rating: this.reviewRating(),
      title: this.reviewTitle(),
      comment: this.reviewComment(),
    }, { withCredentials: true }).subscribe({
      next: () => {
        this.reviewSuccess.set(true);
        this.reviewSubmitting.set(false);
        setTimeout(() => this.showReviewModal.set(false), 1500);
      },
      error: () => {
        this.reviewError.set('No se pudo guardar la reseña. Intenta nuevamente.');
        this.reviewSubmitting.set(false);
      },
    });
  }

  closeReviewModal() {
    this.showReviewModal.set(false);
  }
}
