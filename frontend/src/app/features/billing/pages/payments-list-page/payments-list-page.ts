import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { PaymentsListViewModel } from '../../models/billing.model';
import { BillingApiService } from '../../services/billing-api.service';

@Component({
  selector: 'app-payments-list-page',
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, StatusBadgeComponent, RouterLink],
  templateUrl: './payments-list-page.html',
  styleUrl: './payments-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PaymentsListPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly billingApi = inject(BillingApiService);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<PaymentsListViewModel | null>(null);

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map(params => Number(params.get('page') ?? '1')),
        distinctUntilChanged(),
        switchMap(page => {
          this.viewState.set('loading');
          return this.billingApi.getPayments(page);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: data => {
          this.data.set(data);
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
  }

  goToPage(page: number) {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { page: page > 1 ? page : null },
    });
  }
}
