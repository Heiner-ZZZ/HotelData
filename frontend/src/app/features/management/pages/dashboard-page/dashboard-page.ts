import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import { MetricCardComponent } from '../../../admin/components/metric-card/metric-card';
import { OccupancySummaryComponent } from '../../../admin/components/occupancy-summary/occupancy-summary';
import { RecentReservationsComponent } from '../../../admin/components/recent-reservations/recent-reservations';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { DashboardViewModel } from '../../../admin/models/dashboard.model';
import type { DashboardKpisResponseDto } from '../../../admin/models/dashboard.dto';
import { mapDashboardResponse } from '../../../admin/mappers/dashboard.mapper';

@Component({
  selector: 'app-management-dashboard-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    MetricCardComponent,
    OccupancySummaryComponent,
    PageHeaderComponent,
    RecentReservationsComponent,
    StatusBadgeComponent,
  ],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ManagementDashboardPageComponent {
  private readonly destroyRef = inject(DestroyRef);
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  readonly kpisResource = httpResource<DashboardViewModel | null>(() => '/dashboard/kpis', {
    parse: (dto) => {
      const res = dto as DashboardKpisResponseDto;
      return res.payload ? mapDashboardResponse(res.payload) : null;
    },
  });

  readonly viewState = computed<ViewState>(() => {
    if (this.kpisResource.isLoading()) return 'loading';
    if (this.kpisResource.error()) return 'error';
    const vm = this.kpisResource.value();
    return vm ? 'success' : 'empty';
  });

  readonly errorMessage = computed(() => {
    const err = this.kpisResource.error();
    return (err as unknown as ApiError)?.message || '';
  });

  readonly lastUpdated = signal('');
  readonly isPolling = signal(false);

  readonly lastUpdatedDisplay = computed(() => {
    const val = this.lastUpdated();
    if (!val) return '';
    try {
      const d = new Date(val);
      return d.toLocaleTimeString('es');
    } catch {
      return val;
    }
  });

  constructor() {
    this.destroyRef.onDestroy(() => this.stopPolling());

    effect(() => {
      const vm = this.kpisResource.value();
      if (vm) {
        this.lastUpdated.set(new Date().toISOString());
      }
    });

    effect(() => {
      if (this.viewState() === 'error') {
        this.stopPolling();
      }
    });

    this.startPolling();
  }

  onRetry() {
    this.kpisResource.reload();
    this.startPolling();
  }

  private stopPolling() {
    if (this.pollTimer !== null) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    this.isPolling.set(false);
  }

  private startPolling() {
    this.stopPolling();
    this.isPolling.set(true);
    this.pollTimer = setInterval(() => this.kpisResource.reload(), 60000);
  }
}
