import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { HousekeepingApiService, type HousekeepingDashboard } from '../../services/housekeeping-api.service';

@Component({
  selector: 'app-housekeeping-dashboard-page',
  imports: [RouterLink, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent],
  templateUrl: './housekeeping-dashboard-page.html',
  styleUrl: './housekeeping-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HousekeepingDashboardPageComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly api = inject(HousekeepingApiService);

  readonly viewState = signal<ViewState>('loading');
  readonly dashboard = signal<HousekeepingDashboard | null>(null);

  constructor() {
    this.api
      .getDashboard()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.dashboard.set(data);
          this.viewState.set('success');
        },
        error: () => this.viewState.set('error'),
      });
  }
}
