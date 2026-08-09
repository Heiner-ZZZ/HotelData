import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { GuestsApiService, type GuestBookingItem, type GuestBookingsResponse, type GuestItem, type GuestsResponse } from '../../services/guests-api.service';
import { GpHistoryModalComponent } from './partials/gp-history-modal';

@Component({
  selector: 'app-guests-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    GpHistoryModalComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
  ],
  templateUrl: './guests-page.html',
  styleUrl: './guests-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GuestsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(GuestsApiService);
  readonly propertyCtx = inject(PropertyContextService);

  /**
   * Reactive snapshot of the route's `queryParamMap`. Initialised from
   * `snapshot.queryParamMap` so the first httpResource request fires on direct
   * navigation without a flash of empty URL → loading → real data.
   */
  private readonly queryParamMap = toSignal(this.route.queryParamMap, {
    initialValue: this.route.snapshot.queryParamMap,
  });

  /**
   * Default `Object.is` equality on the resulting `number` already dedups
   * upstream noise, so the legacy `distinctUntilChanged` operator is no longer
   * needed — `computed` rebuilds downstream `httpResource` URLs only when the
   * numeric propId actually changes.
   */
  private readonly routePropId = computed(() =>
    Number(this.queryParamMap().get('prop_id') ?? '0')
  );

  readonly selectedPropId = computed(() => this.routePropId());

  readonly page = signal(1);
  readonly pageSize = signal(20);
  readonly searchQuery = signal('');

  readonly guestsResource = httpResource<GuestsResponse>(() => {
    const propId = this.selectedPropId();
    if (!propId) return undefined;
    return `/api/management/guests?prop_id=${propId}&q=${encodeURIComponent(this.searchQuery())}&page=${this.page()}&page_size=${this.pageSize()}`;
  });

  readonly viewState = computed<ViewState>(() => {
    if (this.selectedPropId() === 0) return 'empty';
    if (this.guestsResource.isLoading()) return 'loading';
    if (this.guestsResource.error()) return 'error';
    return 'success';
  });
  readonly guests = computed<GuestItem[]>(() => this.guestsResource.value()?.items ?? []);
  readonly total = computed(() => this.guestsResource.value()?.total ?? 0);
  readonly hasNext = computed(() => this.guestsResource.value()?.has_next ?? false);

  /** History modal state */
  readonly showHistoryModal = signal(false);
  readonly historyGuestEmail = signal<string | null>(null);
  readonly historyResource = httpResource<GuestBookingsResponse>(() => {
    const propId = this.selectedPropId();
    const email = this.historyGuestEmail();
    if (!propId || !email) return undefined;
    return `/api/management/guests/${encodeURIComponent(email)}/bookings?prop_id=${propId}`;
  });
  readonly historyData = computed(() => this.historyResource.value() ?? null);
  readonly historyBookings = computed<GuestBookingItem[]>(() => this.historyResource.value()?.items ?? []);
  readonly historyLoading = computed(() => this.historyResource.isLoading());
  readonly historyError = computed(() => this.historyResource.error() ? 'No se pudo cargar el historial de reservas.' : '');

  constructor() {
    // Auto-navigate in single-hotel mode
    effect(() => {
      if (this.propertyCtx.ready() && this.propertyCtx.singleHotelMode()) {
        const propId = this.propertyCtx.currentPropId();
        if (propId && !this.routePropId()) {
          void this.router.navigate([], {
            relativeTo: this.route,
            queryParams: { prop_id: propId },
          });
        }
      }
    });
  }

  onPropSelected(event: { propId: number; label: string }): void {
    if (!event.propId) this.propertyCtx.clear();
    this.propertyCtx.setProperty(event.propId, event.label || `Propiedad #${event.propId}`);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null, prop_label: event.label || null },
    });
  }

  onSearch(): void {
    this.page.set(1);
  }

  prevPage(): void {
    if (this.selectedPropId() === 0 || this.page() <= 1) return;
    this.page.update(p => p - 1);
  }

  nextPage(): void {
    if (this.selectedPropId() === 0 || !this.hasNext()) return;
    this.page.update(p => p + 1);
  }

  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.total() / this.pageSize())));

  /** Show booking history for a guest. */
  showHistory(guest: GuestItem): void {
    const propId = this.selectedPropId();
    if (!propId) return;

    this.historyGuestEmail.set(guest.guest_email);
    this.showHistoryModal.set(true);
  }

  closeHistory(): void {
    this.showHistoryModal.set(false);
    this.historyGuestEmail.set(null);
  }

  /** Format currency helper. */
  _money(value: number): string {
    return `$${value.toFixed(2)}`;
  }
}
