import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, linkedSignal, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { httpResource } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';

import { mapRoomHistoryResponse, type RoomHistoryViewModel, type RoomHistoryDto } from './room-history-page.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { HousekeepingSubNavComponent } from '../../components/housekeeping-sub-nav/housekeeping-sub-nav';

const STATUS_META: Record<string, { label: string; icon: string; color: string }> = {
  available:    { label: 'Disponible',    icon: 'check_circle',       color: '#16a34a' },
  occupied:     { label: 'Ocupada',       icon: 'vpn_key',           color: '#2563eb' },
  dirty:        { label: 'Sucia',         icon: 'report',            color: '#dc2626' },
  cleaning:     { label: 'Limpieza',      icon: 'cleaning_services', color: '#ea580c' },
  clean:        { label: 'Limpia',        icon: 'check',             color: '#65a30d' },
  inspected:    { label: 'Inspeccionada', icon: 'fact_check',        color: '#7c3aed' },
  maintenance:  { label: 'Mantenimiento', icon: 'build',             color: '#d97706' },
  out_of_order: { label: 'Fuera de orden', icon: 'block',            color: '#6b7280' },
  out_of_service: { label: 'Fuera de servicio', icon: 'block',      color: '#6b7280' },
};

@Component({
  selector: 'app-room-history-page',
  imports: [DatePipe, FormsModule, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PropertySelectorComponent, RouterLink, HousekeepingSubNavComponent],
  templateUrl: './room-history-page.html',
  styleUrl: './room-history-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoomHistoryPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly propertyCtx = inject(PropertyContextService);

  readonly selectedLabel = signal(this.route.snapshot.queryParamMap.get('prop_label') ?? '');

  // ── URL params → signals (source of truth for filters & pagination) ──
  // Migrated from `pipe(map, distinctUntilChanged)` to Angular's signal graph.
  // `computed` with a custom 4-field `equal` comparator preserves the
  // original dedup semantics so the `httpResource` URL formula + downstream
  // `selectedPropId` / `roomLabelFilter` / `bookingIdFilter` / `currentPage`
  // computeds re-fire only when at least one filter param actually changes.
  private readonly queryParamMap = toSignal(this.route.queryParamMap, {
    initialValue: this.route.snapshot.queryParamMap,
  });

  private readonly queryParams = computed(
    () => {
      const p = this.queryParamMap();
      return {
        propId: Number(p.get('prop_id') ?? '0'),
        roomLabel: p.get('room_label') || '',
        bookingId: p.get('booking_id') || '',
        page: Math.max(1, Number(p.get('page') ?? '1')),
      };
    },
    {
      equal: (a, b) =>
        a.propId === b.propId && a.roomLabel === b.roomLabel &&
        a.bookingId === b.bookingId && a.page === b.page,
    },
  );

  // ── Reactive filter signals synced from URL (for input binding) ──
  readonly selectedPropId = computed(() => this.queryParams().propId);
  readonly roomLabelFilter = computed(() => this.queryParams().roomLabel);
  readonly bookingIdFilter = computed(() => this.queryParams().bookingId);
  readonly currentPage = computed(() => this.queryParams().page);
  readonly pageSize = 20;

  // ── Local mutable copies for editing before submitting ──
  // `linkedSignal` mirrors `queryParams()` automatically (no manual effect) while
  // still allowing local `.set()` overrides from the filters form before the
  // user clicks "Aplicar". This is the canonical Angular 22 pattern already
  // used in `property-selector.ts:47` and `gp-confirm-modal.component.ts:74,76`.
  readonly editPropId = linkedSignal(() => this.queryParams().propId);
  readonly editRoomLabel = linkedSignal(() => this.queryParams().roomLabel);
  readonly editBookingId = linkedSignal(() => this.queryParams().bookingId);

  // ── Data fetching via httpResource (reacts to queryParams changes) ──
  private readonly historyResource = httpResource<RoomHistoryViewModel>(() => {
    const qp = this.queryParams();
    const params = new URLSearchParams();
    params.set('page', String(qp.page));
    params.set('page_size', String(this.pageSize));
    if (qp.propId) params.set('prop_id', String(qp.propId));
    if (qp.roomLabel) params.set('room_label', qp.roomLabel);
    if (qp.bookingId) params.set('booking_id', qp.bookingId);
    return `/api/housekeeping/room-status/history?${params.toString()}`;
  }, {
    parse: (res) => mapRoomHistoryResponse(res as RoomHistoryDto),
  });

  readonly viewState = computed(() => {
    if (this.historyResource.isLoading()) return 'loading' as const;
    if (this.historyResource.error()) return 'error' as const;
    const data = this.historyResource.value();
    if (!data) return 'loading' as const;
    return data.items.length ? 'success' as const : 'empty' as const;
  });

  readonly historyItems = computed(() => this.historyResource.value()?.items ?? []);
  readonly totalItems = computed(() => this.historyResource.value()?.total ?? 0);
  readonly totalPages = computed(() => this.historyResource.value()?.totalPages ?? 0);
  readonly hasPrev = computed(() => this.historyResource.value()?.hasPrev ?? false);
  readonly hasNext = computed(() => this.historyResource.value()?.hasNext ?? false);
  readonly pagesArray = computed(() => Array.from({ length: this.totalPages() }, (_, i) => i + 1));

  // (No constructor needed — `linkedSignal` tracks `queryParams()` lazily, the
  //  first read happens when the template or any consumer calls `editPropId()` /
  //  `editRoomLabel()` / `editBookingId()` during the first change-detection
  //  cycle. This eliminates the timing regression that `effect`-based sync
  //  would have had versus the legacy `subscribe` of `route.queryParamMap`.)

  // ── Property selection ──
  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    this.selectedLabel.set(label);
    if (event.propId) {
      this.propertyCtx.setProperty(event.propId, label);
    } else {
      this.propertyCtx.clear();
    }
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null, prop_label: label || null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  // ── Apply filters (read from edit signals) ──
  applyFilters(): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        prop_id: this.editPropId() || null,
        room_label: this.editRoomLabel() || null,
        booking_id: this.editBookingId() || null,
        page: 1,
      },
      queryParamsHandling: 'merge',
    });
  }

  clearFilters(): void {
    this.editPropId.set(0);
    this.editRoomLabel.set('');
    this.editBookingId.set('');
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: null, room_label: null, booking_id: null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  goToPage(page: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { page: page > 1 ? page : null },
      queryParamsHandling: 'merge',
    });
  }

  // ── Helpers (exposed for template) ──
  getStatusMeta(status: string) {
    return STATUS_META[status] || { label: status, icon: 'help', color: '#9ca3af' };
  }
}
