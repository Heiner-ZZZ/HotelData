import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { HousekeepingApiService, type PaginatedResponse, type RoomStatusItem } from '../../services/housekeeping-api.service';

const STATUS_OPTIONS = [
  { value: 'available', label: 'Disponible' },
  { value: 'occupied', label: 'Ocupada' },
  { value: 'cleaning', label: 'Limpieza' },
  { value: 'clean', label: 'Limpia' },
  { value: 'inspected', label: 'Inspeccionada' },
  { value: 'dirty', label: 'Sucia' },
  { value: 'maintenance', label: 'Mantenimiento' },
  { value: 'out_of_order', label: 'Fuera de orden' },
  { value: 'out_of_service', label: 'Fuera de servicio' },
] as const;

const STATUS_COLORS: Record<string, string> = {
  available: '#16a34a', occupied: '#006076', cleaning: '#d97706',
  clean: '#059669', inspected: '#4338ca', dirty: '#92400e',
  maintenance: '#ba1a1a', out_of_order: '#ba1a1a', out_of_service: '#6f797d',
};

@Component({
  selector: 'app-room-status-page',
  imports: [DatePipe, RouterLink, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, PropertySelectorComponent],
  templateUrl: './room-status-page.html',
  styleUrl: './room-status-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoomStatusPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly propertyCtx = inject(PropertyContextService);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<PaginatedResponse<RoomStatusItem> | null>(null);
  readonly toast = signal<{ type: 'success' | 'error'; message: string } | null>(null);

  readonly statusFilter = signal<string>('');
  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');

  /** Track which rows are currently saving (by room id). */
  readonly savingRow = signal<Set<string>>(new Set());

  readonly statusOptions = [...STATUS_OPTIONS];
  readonly statusColors = STATUS_COLORS;

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => ({
          page: Number(params.get('page') ?? '1'),
          status: params.get('status') ?? '',
          propId: Number(params.get('prop_id') ?? '0'),
          propLabel: params.get('prop_label') ?? '',
        })),
        distinctUntilChanged((a, b) =>
          a.page === b.page && a.status === b.status && a.propId === b.propId
        ),
        switchMap(({ page, status, propId, propLabel }) => {
          this.viewState.set('loading');
          this.statusFilter.set(status);
          this.selectedPropId.set(propId);
          this.selectedLabel.set(propLabel);
          if (!propId) {
            this.propertyCtx.clear();
            return this.api.getRoomStatus(undefined, status || undefined, page);
          }
          this.propertyCtx.setProperty(propId, propLabel || `Propiedad #${propId}`);
          return this.api.syncRoomStatus(propId).pipe(
            switchMap(() => this.api.getRoomStatus(propId, status || undefined, page)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => {
          this.data.set(data);
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
  }

  getStatusColor(status: string): string {
    return STATUS_COLORS[status] ?? '#6f797d';
  }

  getStatusLabel(status: string): string {
    const opt = STATUS_OPTIONS.find((o) => o.value === status);
    return opt?.label ?? status;
  }

  /** Inline update: change status for a specific room. */
  updateStatusInline(item: RoomStatusItem, newStatus: string): void {
    if (newStatus === item.status) return;
    const id = item.id;
    this.savingRow.update((set) => {
      const next = new Set(set);
      next.add(id);
      return next;
    });
    this.toast.set(null);

    this.api
      .upsertRoomStatus({
        prop_id: item.propId,
        room_type_id: item.roomTypeId,
        room_label: item.roomLabel,
        status: newStatus,
        note: item.note || undefined,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.savingRow.update((set) => {
            const next = new Set(set);
            next.delete(id);
            return next;
          });
          this.toast.set({
            type: 'success',
            message: `Hab. ${item.roomLabel} → ${this.getStatusLabel(newStatus)}`,
          });
          this.refresh();
        },
        error: () => {
          this.savingRow.update((set) => {
            const next = new Set(set);
            next.delete(id);
            return next;
          });
          this.toast.set({
            type: 'error',
            message: `Error al actualizar Hab. ${item.roomLabel}`,
          });
        },
      });
  }

  /** Quick action: mark room as dirty (post-checkout). */
  quickDirty(item: RoomStatusItem): void {
    this.updateStatusInline(item, 'dirty');
  }

  /** Quick action: advance clean → inspected. */
  quickInspect(item: RoomStatusItem): void {
    this.updateStatusInline(item, 'inspected');
  }

  /** Quick action: mark as cleaning. */
  quickCleaning(item: RoomStatusItem): void {
    this.updateStatusInline(item, 'cleaning');
  }

  /** Quick action: mark as available. */
  quickAvailable(item: RoomStatusItem): void {
    this.updateStatusInline(item, 'available');
  }

  setStatusFilter(status: string): void {
    this.statusFilter.set(status === this.statusFilter() ? '' : status);
    this.applyFilters();
  }

  private applyFilters(): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        page: null,
        status: this.statusFilter() || null,
        prop_id: this.selectedPropId() || null,
        prop_label: this.selectedLabel() || null,
      },
    });
  }

  goToPage(page: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { page: page > 1 ? page : null },
    });
  }

  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        prop_id: event.propId || null,
        prop_label: label || null,
        status: this.statusFilter() || null,
      },
    });
  }

  private refresh(): void {
    const current = this.data();
    if (!current) return;
    const page = current.page;
    this.viewState.set('loading');
    this.api
      .getRoomStatus(this.selectedPropId() || undefined, this.statusFilter() || undefined, page)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.data.set(data);
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
  }
}
