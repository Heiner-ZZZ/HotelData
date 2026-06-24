import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { MetricCardComponent } from '../../../admin/components/metric-card/metric-card';
import { OccupancySummaryComponent } from '../../../admin/components/occupancy-summary/occupancy-summary';
import { RecentReservationsComponent } from '../../../admin/components/recent-reservations/recent-reservations';
import type { DashboardViewModel } from '../../../admin/models/dashboard.model';
import { DashboardApiService } from '../../../admin/services/dashboard-api.service';

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
  private readonly dashboardApi = inject(DashboardApiService);
  private readonly destroyRef = inject(DestroyRef);
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<DashboardViewModel | null>(null);
  readonly errorMessage = signal('');
  readonly lastUpdated = signal('');
  readonly isPolling = signal(false);
  readonly cacheMessage = signal('');

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
    this.loadKpis();
  }

  onRetry() {
    this.loadKpis();
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
    this.pollTimer = setInterval(() => this.pollKpis(), 30000);
  }

  private pollKpis() {
    this.dashboardApi.getKpis().subscribe({
      next: (result) => {
        if (result) {
          this.viewModel.set(result);
          this.viewState.set('success');
          this.lastUpdated.set(new Date().toISOString());
        }
      },
      error: () => {},
    });
  }

  private loadKpis() {
    this.viewState.set('loading');
    this.errorMessage.set('');
    this.cacheMessage.set('');

    this.dashboardApi.getKpis().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result) => {
        if (result) {
          this.viewModel.set(result);
          this.viewState.set('success');
          this.lastUpdated.set(new Date().toISOString());
          this.startPolling();
        } else {
          this.cacheMessage.set('Aún no hay KPIs cacheados. Ejecuta el pipeline ETL o refresca desde la página de Monitoreo.');
          this.viewState.set('empty');
        }
      },
      error: (error: ApiError) => {
        this.errorMessage.set(error.message || 'No fue posible cargar los indicadores.');
        this.viewState.set('error');
      },
    });
  }
}
