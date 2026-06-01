import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
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
    RecentReservationsComponent
  ],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ManagementDashboardPageComponent {
  private readonly dashboardApi = inject(DashboardApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<DashboardViewModel | null>(null);

  constructor() {
    this.loadDashboard();
  }

  private loadDashboard() {
    this.viewState.set('loading');

    this.dashboardApi
      .getOverview()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (viewModel) => {
          this.viewModel.set(viewModel);
          this.viewState.set(viewModel.kpis.length ? 'success' : 'empty');
        },
        error: () => {
          this.viewState.set('error');
        }
      });
  }
}
