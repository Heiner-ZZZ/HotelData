import { DatePipe, KeyValuePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { NotificationsViewModel } from '../../models/notifications.model';
import { NotificationsApiService } from '../../services/notifications-api.service';

@Component({
  selector: 'app-notifications-page',
  imports: [
    DatePipe,
    EmptyStateComponent,
    ErrorStateComponent,
    KeyValuePipe,
    LoadingStateComponent,
    PageHeaderComponent,
    StatusBadgeComponent
  ],
  templateUrl: './notifications-page.html',
  styleUrl: './notifications-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NotificationsPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly notificationsApi = inject(NotificationsApiService);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<NotificationsViewModel | null>(null);
  readonly errorMessage = signal('');

  readonly typeFilter = signal('');
  readonly startDate = signal('');
  readonly endDate = signal('');

  // Available type filter options (populated from stats)
  readonly typeOptions = signal<Array<{ key: string; label: string }>>([]);

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map((params) => ({
          page: Number(params.get('page') ?? '1'),
          type: params.get('type') || '',
          startDate: params.get('start_date') || '',
          endDate: params.get('end_date') || ''
        })),
        distinctUntilChanged((a, b) =>
          a.page === b.page && a.type === b.type &&
          a.startDate === b.startDate && a.endDate === b.endDate
        ),
        switchMap(({ page, type, startDate, endDate }) => {
          this.viewState.set('loading');
          this.typeFilter.set(type);
          this.startDate.set(startDate);
          this.endDate.set(endDate);
          return this.notificationsApi.getNotifications(page, type || undefined, startDate || undefined, endDate || undefined);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (data) => {
          this.data.set(data);
          // Populate type options from stats
          const types = Object.keys(data.stats.byType).map((key) => ({
            key,
            label: this.typeLabel(key)
          }));
          this.typeOptions.set(types);
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => {
          this.errorMessage.set('No fue posible cargar las notificaciones.');
          this.viewState.set('error');
        }
      });
  }

  typeLabel(type: string): string {
    const labels: Record<string, string> = {
      staff_new_booking: 'Staff — Nueva reserva',
      guest_confirmed: 'Cliente — Confirmada',
      guest_rejected: 'Cliente — Rechazada',
      guest_other: 'Cliente — Otro'
    };
    return labels[type] || type;
  }

  filterByType(type: string) {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { type: type || null, page: null }
    });
  }

  /** Apply a quick date range preset (N days back from today) and navigate. */
  setQuickRange(days: number) {
    const today = new Date();
    const start = new Date(today);
    start.setDate(start.getDate() - days);
    this.startDate.set(start.toISOString().slice(0, 10));
    this.endDate.set(today.toISOString().slice(0, 10));
    this.setDateRange();
  }

  /** Apply 'Este mes' preset (1st of month → today) and navigate. */
  setQuickMonth() {
    const today = new Date();
    const start = new Date(today.getFullYear(), today.getMonth(), 1);
    this.startDate.set(start.toISOString().slice(0, 10));
    this.endDate.set(today.toISOString().slice(0, 10));
    this.setDateRange();
  }

  setDateRange() {
    const sd = this.startDate();
    const ed = this.endDate();
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: {
        start_date: sd || null,
        end_date: ed || null,
        page: null
      }
    });
  }

  clearDateFilter() {
    this.startDate.set('');
    this.endDate.set('');
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { start_date: null, end_date: null, page: null }
    });
  }

  clearFilter() {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { type: null, page: null }
    });
  }

  goToPage(page: number) {
    const type = this.typeFilter();
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { type: type || null, page: page > 1 ? page : null }
    });
  }

  /** Format a date N days ago (or today if days=0) as YYYY-MM-DD. */
  todayISO(daysAgo: number): string {
    const d = new Date();
    d.setDate(d.getDate() - daysAgo);
    return d.toISOString().slice(0, 10);
  }

  /** First day of the current month as YYYY-MM-DD. */
  monthStartISO(): string {
    const d = new Date();
    d.setDate(1);
    return d.toISOString().slice(0, 10);
  }

  statusTone(status: string): 'success' | 'warning' | 'danger' {
    return status === 'sent' ? 'success' : status === 'failed' ? 'warning' : 'danger';
  }
}
