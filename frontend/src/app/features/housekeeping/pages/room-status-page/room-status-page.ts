import { SlicePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { HousekeepingApiService, type PaginatedResponse, type RoomStatusItem } from '../../services/housekeeping-api.service';

const STATUS_OPTIONS = ['available', 'occupied', 'cleaning', 'maintenance', 'out_of_order'] as const;

@Component({
  selector: 'app-room-status-page',
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule, SlicePipe],

  templateUrl: './room-status-page.html',
  styleUrl: './room-status-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoomStatusPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly propertyCtx = inject(PropertyContextService);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<PaginatedResponse<RoomStatusItem> | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly statusFilter = signal<string>('');
  readonly propFilter = signal<number>(0);
  readonly dropdownOpen = signal(false);
  readonly propertyOptions = signal<Array<{ propId: number; label: string }>>([]);

  readonly statusForm = this.formBuilder.nonNullable.group({
    newStatus: ['available', Validators.required],
    note: [''],
  });

  readonly statusOptions = [...STATUS_OPTIONS];

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => ({
          page: Number(params.get('page') ?? '1'),
          status: params.get('status') ?? '',
          propId: Number(params.get('prop_id') ?? '0'),
        })),
        distinctUntilChanged((a, b) => a.page === b.page && a.status === b.status && a.propId === b.propId),
        switchMap(({ page, status, propId }) => {
          this.viewState.set('loading');
          this.statusFilter.set(status);
          this.propFilter.set(propId);
          if (!propId) {
            this.propertyCtx.clear();
            return this.api.getRoomStatus(undefined, status || undefined, page);
          }
          this.propertyCtx.setProperty(propId, `Propiedad #${propId}`);
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
          this.populatePropertyOptions(data);
        },
        error: () => this.viewState.set('error'),
      });
  }

  private populatePropertyOptions(data: PaginatedResponse<RoomStatusItem>): void {
    const propSet = new Set(data.items.map((i) => i.propId));
    const options = Array.from(propSet).map((id) => ({
      propId: id,
      label: `Propiedad #${id}`,
    }));
    if (options.length && !this.propertyOptions().length) {
      this.propertyOptions.set(options);
    }
  }

  selectProperty(propId: number): void {
    this.propFilter.set(propId);
    this.dropdownOpen.set(false);
    this.applyFilters();
  }

  clearProperty(): void {
    this.propFilter.set(0);
    this.applyFilters();
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
        prop_id: this.propFilter() || null,
      },
    });
  }

  goToPage(page: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { page: page > 1 ? page : null },
    });
  }

  updateStatus(item: RoomStatusItem): void {
    this.api
      .upsertRoomStatus({
        prop_id: item.propId,
        room_type_id: item.roomTypeId,
        room_label: item.roomLabel,
        status: this.statusForm.controls.newStatus.value,
        note: this.statusForm.controls.note.value || undefined,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.message.set(`Habitación ${item.roomLabel} actualizada`);
          this.errorMessage.set('');
          this.refresh();
        },
        error: (err) => {
          this.errorMessage.set(err.message || 'Error al actualizar estado');
          this.message.set('');
        },
      });
  }

  private refresh(): void {
    const current = this.data();
    if (!current) return;
    const page = current.page;
    this.viewState.set('loading');
    this.api
      .getRoomStatus(this.propFilter() || undefined, this.statusFilter() || undefined, page)
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
