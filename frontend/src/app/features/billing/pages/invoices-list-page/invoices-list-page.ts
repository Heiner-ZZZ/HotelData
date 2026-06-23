import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { CurrencyPipe } from '@angular/common';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { InvoicesListViewModel } from '../../models/billing.model';
import { BillingApiService } from '../../services/billing-api.service';

@Component({
  selector: 'app-invoices-list-page',
  imports: [CurrencyPipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, StatusBadgeComponent, RouterLink],
  templateUrl: './invoices-list-page.html',
  styleUrl: './invoices-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InvoicesListPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly billingApi = inject(BillingApiService);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<InvoicesListViewModel | null>(null);

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map(params => Number(params.get('page') ?? '1')),
        distinctUntilChanged(),
        switchMap(page => {
          this.viewState.set('loading');
          return this.billingApi.getInvoices(page);
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
