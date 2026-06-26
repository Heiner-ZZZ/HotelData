import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import type { ApiError } from '../../../../core/api/api-error.model';
import { toast } from '../../../../core/toast/toast.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { MetricCardComponent } from '../../components/metric-card/metric-card';
import { OccupancySummaryComponent } from '../../components/occupancy-summary/occupancy-summary';
import { RecentReservationsComponent } from '../../components/recent-reservations/recent-reservations';
import type { DashboardViewModel } from '../../models/dashboard.model';
import { DashboardApiService } from '../../services/dashboard-api.service';

@Component({
  selector: 'app-dashboard-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    MetricCardComponent,
    OccupancySummaryComponent,
    PageHeaderComponent,
    RecentReservationsComponent
  ],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DashboardPageComponent {
  private readonly dashboardApi = inject(DashboardApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<DashboardViewModel | null>(null);
  readonly errorMessage = signal('');

  constructor() {
    this.loadDashboard();
  }

  onRetry() {
    this.loadDashboard();
  }

  refreshKpis(): void {
    this.dashboardApi
      .refreshKpis()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          if (result.ok) {
            toast(result.display_message, 'dark', 5000);
            this.loadDashboard();
          } else {
            toast('No se pudieron actualizar los indicadores.', 'error', 5000);
          }
        },
        error: (err: ApiError) => {
          toast(err.message || 'Error al refrescar los indicadores del panel.', 'error', 5000);
        },
      });
  }

  private loadDashboard() {
    this.viewState.set('loading');
    this.errorMessage.set('');

    this.dashboardApi
      .getOverview()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (viewModel) => {
          this.viewModel.set(viewModel);
          this.viewState.set(viewModel.kpis.length ? 'success' : 'empty');
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible cargar los indicadores del panel.');
          this.viewState.set('error');
        }
      });
  }
}
