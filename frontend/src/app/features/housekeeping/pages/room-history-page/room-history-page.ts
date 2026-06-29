import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { httpResource } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { distinctUntilChanged, map } from 'rxjs';

import type { RoomStatusHistoryEntry } from '../../services/housekeeping-api.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';

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
  imports: [DatePipe, FormsModule, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, RouterLink],
  templateUrl: './room-history-page.html',
  styleUrl: './room-history-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoomHistoryPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  // ── URL params → signals (source of truth for filters & pagination) ──
  private readonly queryParams = toSignal(
    this.route.queryParamMap.pipe(
      map((params) => ({
        propId: Number(params.get('prop_id') ?? '0'),
        roomLabel: params.get('room_label') || '',
        bookingId: params.get('booking_id') || '',
        page: Math.max(1, Number(params.get('page') ?? '1')),
      })),
      distinctUntilChanged((a, b) =>
        a.propId === b.propId && a.roomLabel === b.roomLabel &&
        a.bookingId === b.bookingId && a.page === b.page
      ),
    ),
    { initialValue: { propId: 0, roomLabel: '', bookingId: '', page: 1 } }
  );

  // ── Reactive filter signals synced from URL (for input binding) ──
  readonly propIdFilter = computed(() => this.queryParams().propId);
  readonly roomLabelFilter = computed(() => this.queryParams().roomLabel);
  readonly bookingIdFilter = computed(() => this.queryParams().bookingId);
  readonly currentPage = computed(() => this.queryParams().page);
  readonly pageSize = 20;

  // ── Local mutable copies for editing before submitting ──
  readonly editPropId = signal(0);
  readonly editRoomLabel = signal('');
  readonly editBookingId = signal('');

  // ── Data fetching via httpResource (reacts to queryParams changes) ──
  private readonly historyResource = httpResource<{
    items: RoomStatusHistoryEntry[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  }>(() => {
    const qp = this.queryParams();
    const params = new URLSearchParams();
    params.set('page', String(qp.page));
    params.set('page_size', String(this.pageSize));
    if (qp.propId) params.set('prop_id', String(qp.propId));
    if (qp.roomLabel) params.set('room_label', qp.roomLabel);
    if (qp.bookingId) params.set('booking_id', qp.bookingId);
    return `/api/housekeeping/room-status/history?${params.toString()}`;
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
  readonly totalPages = computed(() => this.historyResource.value()?.total_pages ?? 0);
  readonly hasPrev = computed(() => this.historyResource.value()?.has_prev ?? false);
  readonly hasNext = computed(() => this.historyResource.value()?.has_next ?? false);
  readonly pagesArray = computed(() => Array.from({ length: this.totalPages() }, (_, i) => i + 1));

  constructor() {
    // Sync URL params into edit signals on mount/navigation
    this.queryParams();
    // Re-initialize edit signals from URL on change
    this.route.queryParamMap.pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((params) => {
      this.editPropId.set(Number(params.get('prop_id') ?? '0'));
      this.editRoomLabel.set(params.get('room_label') || '');
      this.editBookingId.set(params.get('booking_id') || '');
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
